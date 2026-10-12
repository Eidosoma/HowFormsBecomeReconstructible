from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import jax
import jax.numpy as jnp
import numpy as np
from numpy.typing import NDArray

from fep_lab.integrity import read_json, sha256_bytes
from fep_lab.seeds import derive_seed
from fep_ph18.state import BodyState, normalized_entropy, state_features

from .config import MODEL_ACTIONS, ExperimentConfig
from .types import ConditionSpec


OUTPUTS = 5  # inherited, completion, next regime A/B/shock
PARAMETER_NAMES = (
    "wz",
    "uz",
    "bz",
    "wr",
    "ur",
    "br",
    "wh",
    "uh",
    "bh",
    "head",
)


@dataclass(frozen=True)
class Projection:
    mean: NDArray[np.float64]
    components: NDArray[np.float64]

    def validate(self) -> None:
        if self.mean.shape != (100,) or self.components.ndim != 2:
            raise ValueError("recurrent CLR projection shape is invalid")
        if self.components.shape[1] != 100:
            raise ValueError("recurrent projection must act on 100 components")
        if not np.all(np.isfinite(self.mean)) or not np.all(np.isfinite(self.components)):
            raise ValueError("recurrent projection contains non-finite values")

    def project(self, clr: NDArray[np.floating]) -> NDArray[np.float64]:
        return (np.asarray(clr, dtype=np.float64) - self.mean) @ self.components.T


@dataclass(frozen=True)
class SequenceCorpus:
    features: NDArray[np.float64]
    actions: NDArray[np.int32]
    targets: NDArray[np.float64]
    mask: NDArray[np.float64]
    matrix_ids: NDArray[np.int32]
    projection: Projection
    feature_mean: NDArray[np.float64]
    feature_scale: NDArray[np.float64]

    def validate(self) -> None:
        n, steps, width = self.features.shape
        if self.actions.shape != (n, steps) or self.targets.shape != (n, steps, OUTPUTS):
            raise ValueError("recurrent corpus shapes do not align")
        if self.mask.shape != (n, steps) or self.matrix_ids.shape != (n,):
            raise ValueError("recurrent corpus mask or matrix shape is invalid")
        if self.feature_mean.shape != (width,) or self.feature_scale.shape != (width,):
            raise ValueError("recurrent corpus standardization shape is invalid")
        if np.any(self.feature_scale <= 0.0):
            raise ValueError("recurrent feature scale is not positive")
        self.projection.validate()


@dataclass(frozen=True)
class RecurrentModel:
    projection: Projection
    feature_mean: NDArray[np.float64]
    feature_scale: NDArray[np.float64]
    parameters: dict[str, NDArray[np.float64]]
    qualification: dict[str, float | bool]

    @property
    def members(self) -> int:
        return int(self.parameters["bz"].shape[0])

    @property
    def hidden_width(self) -> int:
        return int(self.parameters["bz"].shape[1])

    @property
    def feature_width(self) -> int:
        return int(self.feature_mean.shape[0])

    def validate(self) -> None:
        self.projection.validate()
        m, h, f = self.members, self.hidden_width, self.feature_width
        expected = {
            "wz": (m, f, h),
            "uz": (m, h, h),
            "bz": (m, h),
            "wr": (m, f, h),
            "ur": (m, h, h),
            "br": (m, h),
            "wh": (m, f, h),
            "uh": (m, h, h),
            "bh": (m, h),
            "head": (m, MODEL_ACTIONS, h + 1, OUTPUTS),
        }
        if set(self.parameters) != set(expected):
            raise ValueError("recurrent parameter set is incomplete")
        for name, shape in expected.items():
            value = self.parameters[name]
            if value.shape != shape or not np.all(np.isfinite(value)):
                raise ValueError(f"recurrent parameter {name} is invalid")
        if self.feature_scale.shape != (f,) or np.any(self.feature_scale <= 0.0):
            raise ValueError("recurrent feature scaling is invalid")

    def initial_hidden(self) -> NDArray[np.float64]:
        return np.zeros((self.members, self.hidden_width), dtype=np.float64)

    def features(self, state: BodyState, condition: ConditionSpec) -> NDArray[np.float64]:
        rich = state_features(state, condition, rich=True)
        base = np.concatenate((self.projection.project(rich[:100]), rich[100:]))
        return (base - self.feature_mean) / self.feature_scale

    def predict_all(
        self,
        hidden: NDArray[np.floating],
        state: BodyState,
        condition: ConditionSpec,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        values = np.asarray(hidden, dtype=np.float64)
        if values.shape != (self.members, self.hidden_width):
            raise ValueError("recurrent hidden state shape is invalid")
        x = self.features(state, condition)
        following: list[NDArray[np.float64]] = []
        outputs: list[NDArray[np.float64]] = []
        for member in range(self.members):
            params = {name: value[member] for name, value in self.parameters.items()}
            h = _gru_numpy(params, values[member], x)
            design = np.concatenate((np.asarray((1.0,)), h))
            logits = np.einsum("d,ado->ao", design, params["head"])
            binary = 1.0 / (1.0 + np.exp(-np.clip(logits[:, :2], -40.0, 40.0)))
            regime = _softmax_numpy(logits[:, 2:])
            following.append(h)
            outputs.append(np.concatenate((binary, regime), axis=1))
        return np.stack(following), np.mean(np.stack(outputs), axis=0)


def _fit_projection(clr: NDArray[np.float64], components: int) -> Projection:
    mean = clr.mean(axis=0)
    _u, _s, right = np.linalg.svd(clr - mean, full_matrices=False)
    selected = right[:components].copy()
    for index in range(len(selected)):
        pivot = int(np.argmax(np.abs(selected[index])))
        if selected[index, pivot] < 0.0:
            selected[index] *= -1.0
    projection = Projection(mean, selected)
    projection.validate()
    return projection


def load_sequence_corpus(
    cell_paths: Iterable[Path], config: ExperimentConfig
) -> SequenceCorpus:
    loaded: list[tuple[dict[str, NDArray[Any]], dict[str, Any]]] = []
    clr_rows: list[NDArray[np.float64]] = []
    for path in sorted(Path(value) for value in cell_paths):
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        metadata = read_json(path.with_suffix(".json"))
        loaded.append((arrays, metadata))
        clr_rows.append(np.asarray(arrays["rich_features"][:, :100], dtype=np.float64))
    if not loaded:
        raise RuntimeError("no development cells were supplied to the recurrent model")
    projection = _fit_projection(np.concatenate(clr_rows), config.clr_components)
    sequences: list[tuple[NDArray[np.float64], NDArray[np.int32], NDArray[np.float64], int]] = []
    for arrays, _metadata in loaded:
        transformed = np.concatenate(
            (
                projection.project(arrays["rich_features"][:, :100]),
                np.asarray(arrays["rich_features"][:, 100:], dtype=np.float64),
            ),
            axis=1,
        )
        keys = np.column_stack((arrays["matrix_id"], arrays["episode"]))
        for matrix, episode in sorted({tuple(int(v) for v in row) for row in keys}):
            selected = (arrays["matrix_id"] == matrix) & (arrays["episode"] == episode)
            order = np.argsort(arrays["step"][selected], kind="stable")
            features = transformed[selected][order]
            actions = np.asarray(arrays["action"][selected][order], dtype=np.int32)
            completed = np.asarray(arrays["completed"][selected][order], dtype=np.float64)
            inherited = (
                (completed > 0.5)
                & (np.asarray(arrays["next_similarity"][selected][order]) >= 0.90)
            ).astype(np.float64)
            regimes = np.eye(3, dtype=np.float64)[
                np.asarray(arrays["next_regime"][selected][order], dtype=np.int32)
            ]
            targets = np.column_stack((inherited, completed, regimes))
            sequences.append((features, actions, targets, matrix))
    maximum = max(len(value[0]) for value in sequences)
    count = len(sequences)
    width = sequences[0][0].shape[1]
    feature_values = np.zeros((count, maximum, width), dtype=np.float64)
    actions = np.zeros((count, maximum), dtype=np.int32)
    targets = np.zeros((count, maximum, OUTPUTS), dtype=np.float64)
    mask = np.zeros((count, maximum), dtype=np.float64)
    matrices = np.zeros(count, dtype=np.int32)
    for index, (features, action, target, matrix) in enumerate(sequences):
        length = len(features)
        feature_values[index, :length] = features
        actions[index, :length] = action
        targets[index, :length] = target
        mask[index, :length] = 1.0
        matrices[index] = matrix
    flattened = feature_values[mask.astype(bool)]
    mean = flattened.mean(axis=0)
    scale = flattened.std(axis=0)
    scale[scale < 1.0e-8] = 1.0
    feature_values = (feature_values - mean) / scale
    corpus = SequenceCorpus(
        feature_values,
        actions,
        targets,
        mask,
        matrices,
        projection,
        mean,
        scale,
    )
    corpus.validate()
    return corpus


def _sigmoid_jax(value: jax.Array) -> jax.Array:
    return jax.nn.sigmoid(value)


def _gru_jax(params: dict[str, jax.Array], hidden: jax.Array, x: jax.Array) -> jax.Array:
    z = _sigmoid_jax(x @ params["wz"] + hidden @ params["uz"] + params["bz"])
    r = _sigmoid_jax(x @ params["wr"] + hidden @ params["ur"] + params["br"])
    candidate = jnp.tanh(x @ params["wh"] + (r * hidden) @ params["uh"] + params["bh"])
    return (1.0 - z) * hidden + z * candidate


def _sequence_logits(params: dict[str, jax.Array], sequence: jax.Array) -> jax.Array:
    hidden = jnp.zeros(params["bz"].shape[0], dtype=jnp.float64)

    def step(h: jax.Array, x: jax.Array) -> tuple[jax.Array, jax.Array]:
        following = _gru_jax(params, h, x)
        design = jnp.concatenate((jnp.ones(1, dtype=jnp.float64), following))
        logits = jnp.einsum("d,ado->ao", design, params["head"])
        return following, logits

    _hidden, logits = jax.lax.scan(step, hidden, sequence)
    return logits


def _batch_logits(params: dict[str, jax.Array], features: jax.Array) -> jax.Array:
    return jax.vmap(lambda value: _sequence_logits(params, value))(features)


def _loss(
    params: dict[str, jax.Array],
    features: jax.Array,
    actions: jax.Array,
    targets: jax.Array,
    mask: jax.Array,
) -> jax.Array:
    all_logits = _batch_logits(params, features)
    action_indices = jnp.broadcast_to(
        actions[:, :, None, None], actions.shape + (1, OUTPUTS)
    )
    selected = jnp.take_along_axis(
        all_logits,
        action_indices,
        axis=2,
    )[:, :, 0, :]
    binary = jnp.mean(
        jnp.square(jax.nn.sigmoid(selected[:, :, :2]) - targets[:, :, :2]),
        axis=-1,
    )
    regime = -jnp.sum(
        targets[:, :, 2:] * jax.nn.log_softmax(selected[:, :, 2:], axis=-1),
        axis=-1,
    )
    return jnp.sum(mask * (binary + 0.25 * regime)) / jnp.maximum(jnp.sum(mask), 1.0)


def _initialize(
    seed: int, feature_width: int, hidden_width: int
) -> dict[str, jax.Array]:
    key = jax.random.PRNGKey(np.uint32(seed & 0xFFFFFFFF))
    keys = jax.random.split(key, 7)
    input_scale = 1.0 / np.sqrt(feature_width)
    hidden_scale = 1.0 / np.sqrt(hidden_width)
    return {
        "wz": jax.random.normal(keys[0], (feature_width, hidden_width), dtype=jnp.float64) * input_scale,
        "uz": jax.random.normal(keys[1], (hidden_width, hidden_width), dtype=jnp.float64) * hidden_scale,
        "bz": jnp.zeros(hidden_width, dtype=jnp.float64),
        "wr": jax.random.normal(keys[2], (feature_width, hidden_width), dtype=jnp.float64) * input_scale,
        "ur": jax.random.normal(keys[3], (hidden_width, hidden_width), dtype=jnp.float64) * hidden_scale,
        "br": jnp.zeros(hidden_width, dtype=jnp.float64),
        "wh": jax.random.normal(keys[4], (feature_width, hidden_width), dtype=jnp.float64) * input_scale,
        "uh": jax.random.normal(keys[5], (hidden_width, hidden_width), dtype=jnp.float64) * hidden_scale,
        "bh": jnp.zeros(hidden_width, dtype=jnp.float64),
        "head": jax.random.normal(
            keys[6], (MODEL_ACTIONS, hidden_width + 1, OUTPUTS), dtype=jnp.float64
        ) * hidden_scale,
    }


def _adam_train(
    initial: dict[str, jax.Array],
    features: jax.Array,
    actions: jax.Array,
    targets: jax.Array,
    mask: jax.Array,
    epochs: int,
    learning_rate: float,
) -> dict[str, jax.Array]:
    value_and_grad = jax.jit(jax.value_and_grad(_loss))
    params = initial
    first = jax.tree_util.tree_map(jnp.zeros_like, params)
    second = jax.tree_util.tree_map(jnp.zeros_like, params)
    beta1, beta2 = 0.9, 0.999
    for epoch in range(1, int(epochs) + 1):
        _value, gradients = value_and_grad(params, features, actions, targets, mask)
        first = jax.tree_util.tree_map(
            lambda m, g: beta1 * m + (1.0 - beta1) * g, first, gradients
        )
        second = jax.tree_util.tree_map(
            lambda v, g: beta2 * v + (1.0 - beta2) * jnp.square(g), second, gradients
        )
        correction1 = 1.0 - beta1**epoch
        correction2 = 1.0 - beta2**epoch
        params = jax.tree_util.tree_map(
            lambda p, m, v: p
            - learning_rate
            * (m / correction1)
            / (jnp.sqrt(v / correction2) + 1.0e-8),
            params,
            first,
            second,
        )
    return params


def _probabilities(logits: NDArray[np.float64]) -> NDArray[np.float64]:
    binary = 1.0 / (1.0 + np.exp(-np.clip(logits[..., :2], -40.0, 40.0)))
    shifted = logits[..., 2:] - np.max(logits[..., 2:], axis=-1, keepdims=True)
    regime = np.exp(shifted)
    regime /= regime.sum(axis=-1, keepdims=True)
    return np.concatenate((binary, regime), axis=-1)


def _action_order_concordance(
    targets: NDArray[np.float64],
    predictions: NDArray[np.float64],
    actions: NDArray[np.int32],
    mask: NDArray[np.bool_],
) -> float:
    observed: list[float] = []
    forecast: list[float] = []
    for action in range(MODEL_ACTIONS):
        selected = mask & (actions == action)
        if not np.any(selected):
            continue
        observed.append(float(targets[..., 0][selected].mean()))
        forecast.append(float(predictions[..., action, 0][selected].mean()))
    concordant = 0
    total = 0
    for left in range(len(observed)):
        for right in range(left + 1, len(observed)):
            if observed[left] == observed[right]:
                continue
            concordant += int(
                np.sign(observed[left] - observed[right])
                == np.sign(forecast[left] - forecast[right])
            )
            total += 1
    return float(concordant / total) if total else 0.5


def fit_recurrent_model(
    corpus: SequenceCorpus,
    config: ExperimentConfig,
    *,
    exact_action_concordance: float,
) -> RecurrentModel:
    corpus.validate()
    features = jnp.asarray(corpus.features, dtype=jnp.float64)
    actions = jnp.asarray(corpus.actions, dtype=jnp.int32)
    targets = jnp.asarray(corpus.targets, dtype=jnp.float64)
    heldout_predictions = np.zeros(
        corpus.targets.shape[:2] + (MODEL_ACTIONS, OUTPUTS), dtype=np.float64
    )
    parameters: dict[str, list[NDArray[np.float64]]] = {
        name: [] for name in PARAMETER_NAMES
    }
    for fold in range(config.ensemble_members):
        training_sequences = (corpus.matrix_ids % config.ensemble_members) != fold
        training_mask = jnp.asarray(
            corpus.mask * training_sequences[:, None], dtype=jnp.float64
        )
        seed = derive_seed(config.master_seed, "fep_ph19.recurrent.member", fold)
        initial = _initialize(seed, corpus.features.shape[-1], config.recurrent_hidden_width)
        fitted = _adam_train(
            initial,
            features,
            actions,
            targets,
            training_mask,
            config.recurrent_epochs,
            config.recurrent_learning_rate,
        )
        logits = np.asarray(_batch_logits(fitted, features), dtype=np.float64)
        heldout = (corpus.matrix_ids % config.ensemble_members) == fold
        heldout_predictions[heldout] = _probabilities(logits[heldout])
        for name in PARAMETER_NAMES:
            parameters[name].append(np.asarray(fitted[name], dtype=np.float64))
    mask = corpus.mask.astype(bool)
    action_indices = np.broadcast_to(
        corpus.actions[:, :, None, None],
        corpus.actions.shape + (1, OUTPUTS),
    )
    selected = np.take_along_axis(
        heldout_predictions,
        action_indices,
        axis=2,
    )[:, :, 0, :]
    inherited = corpus.targets[..., 0][mask]
    completion = corpus.targets[..., 1][mask]
    regimes = corpus.targets[..., 2:][mask]
    inherited_prediction = selected[..., 0][mask]
    completion_prediction_grid = selected[..., 1]
    completion_prediction = completion_prediction_grid[mask]
    regime_prediction = selected[..., 2:][mask]
    inherited_brier = float(np.mean((inherited - inherited_prediction) ** 2))
    completion_brier = float(np.mean((completion - completion_prediction) ** 2))
    inherited_intercept = float(np.mean((inherited - inherited.mean()) ** 2))
    completion_intercept = float(np.mean((completion - completion.mean()) ** 2))
    regime_brier = float(np.mean((regimes - regime_prediction) ** 2))
    regime_uniform_brier = float(np.mean((regimes - 1.0 / 3.0) ** 2))
    sequence_errors = []
    for index in range(len(corpus.features)):
        valid = mask[index]
        if np.any(valid):
            sequence_errors.append(
                abs(
                    float(completion_prediction_grid[index, valid].mean())
                    - float(corpus.targets[index, valid, 1].mean())
                )
            )
    concordance = _action_order_concordance(
        corpus.targets,
        heldout_predictions,
        corpus.actions,
        mask,
    )
    qualification: dict[str, float | bool] = {
        "inherited_brier": inherited_brier,
        "inherited_intercept_brier": inherited_intercept,
        "inherited_skill": float(
            1.0 - inherited_brier / max(inherited_intercept, 1.0e-12)
        ),
        "completion_brier": completion_brier,
        "completion_intercept_brier": completion_intercept,
        "completion_skill": float(
            1.0 - completion_brier / max(completion_intercept, 1.0e-12)
        ),
        "regime_brier": regime_brier,
        "regime_uniform_brier": regime_uniform_brier,
        "regime_skill": float(
            1.0 - regime_brier / max(regime_uniform_brier, 1.0e-12)
        ),
        "action_order_concordance": concordance,
        "exact_action_concordance": float(exact_action_concordance),
        "sequence_completion_calibration_mae": float(np.mean(sequence_errors)),
    }
    qualification["qualified"] = bool(
        qualification["inherited_skill"] > 0.0
        and qualification["completion_skill"] > 0.0
        and qualification["regime_skill"] > 0.0
        and concordance >= exact_action_concordance - config.recurrent_action_tolerance
        and qualification["sequence_completion_calibration_mae"] < 0.15
    )
    model = RecurrentModel(
        corpus.projection,
        corpus.feature_mean,
        corpus.feature_scale,
        {name: np.stack(values) for name, values in parameters.items()},
        qualification,
    )
    model.validate()
    return model


def _sigmoid_numpy(value: NDArray[np.float64]) -> NDArray[np.float64]:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -40.0, 40.0)))


def _softmax_numpy(value: NDArray[np.float64]) -> NDArray[np.float64]:
    shifted = np.asarray(value, dtype=np.float64) - np.max(value, axis=-1, keepdims=True)
    weights = np.exp(shifted)
    return weights / weights.sum(axis=-1, keepdims=True)


def _gru_numpy(
    params: dict[str, NDArray[np.float64]],
    hidden: NDArray[np.float64],
    x: NDArray[np.float64],
) -> NDArray[np.float64]:
    z = _sigmoid_numpy(x @ params["wz"] + hidden @ params["uz"] + params["bz"])
    r = _sigmoid_numpy(x @ params["wr"] + hidden @ params["ur"] + params["br"])
    candidate = np.tanh(x @ params["wh"] + (r * hidden) @ params["uh"] + params["bh"])
    return (1.0 - z) * hidden + z * candidate


def model_arrays(model: RecurrentModel) -> dict[str, NDArray[Any]]:
    names = sorted(model.qualification)
    output: dict[str, NDArray[Any]] = {
        "projection_mean": model.projection.mean,
        "projection_components": model.projection.components,
        "feature_mean": model.feature_mean,
        "feature_scale": model.feature_scale,
        "qualification_names": np.asarray(names),
        "qualification_values": np.asarray(
            [float(model.qualification[name]) for name in names], dtype=np.float64
        ),
    }
    output.update({f"parameter_{name}": value for name, value in model.parameters.items()})
    return output


def model_from_arrays(arrays: dict[str, NDArray[Any]]) -> RecurrentModel:
    names = [str(value) for value in arrays["qualification_names"]]
    values = [float(value) for value in arrays["qualification_values"]]
    qualification: dict[str, float | bool] = dict(zip(names, values, strict=True))
    if "qualified" in qualification:
        qualification["qualified"] = bool(qualification["qualified"])
    model = RecurrentModel(
        Projection(
            np.asarray(arrays["projection_mean"], dtype=np.float64),
            np.asarray(arrays["projection_components"], dtype=np.float64),
        ),
        np.asarray(arrays["feature_mean"], dtype=np.float64),
        np.asarray(arrays["feature_scale"], dtype=np.float64),
        {
            name: np.asarray(arrays[f"parameter_{name}"], dtype=np.float64)
            for name in PARAMETER_NAMES
        },
        qualification,
    )
    model.validate()
    return model


def save_model(path: Path, model: RecurrentModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **model_arrays(model))


def load_model(path: Path) -> RecurrentModel:
    with np.load(path, allow_pickle=False) as archive:
        return model_from_arrays({name: archive[name].copy() for name in archive.files})


def model_digest(model: RecurrentModel) -> str:
    chunks: list[bytes] = []
    for name, array in sorted(model_arrays(model).items()):
        value = np.ascontiguousarray(array)
        chunks.extend(
            (name.encode(), str(value.shape).encode(), value.dtype.str.encode(), value.tobytes())
        )
    return sha256_bytes(b"".join(chunks))


__all__ = (
    "RecurrentModel",
    "SequenceCorpus",
    "fit_recurrent_model",
    "load_model",
    "load_sequence_corpus",
    "model_arrays",
    "model_digest",
    "save_model",
)
