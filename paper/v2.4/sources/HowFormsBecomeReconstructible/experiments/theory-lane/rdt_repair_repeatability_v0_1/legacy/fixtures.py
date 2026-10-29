"""Disposable synthetic records; keys/stage never overlap scientific futures."""
import hashlib
import numpy as np
from study import e, REGIMES


def panel():
    random = np.random.default_rng(2026101701)
    rows, forecasts, outcomes, packets = [], [], [], []
    for block, classes in ((-2, (0, 1, 1)), (-1, (0, 0, 1, 1))):
        for i, current in enumerate(classes):
            signs = 1 - 2 * random.integers(0, 2, (16, 16))
            signs[e.PORTS[0]] = 1
            packet = np.stack((signs * np.roll(signs, -1, 1), signs * np.roll(signs, -1, 0))).astype(float) * .7
            packet[:, 5:7, 5:7] = 0
            if i == 1:
                packet[:] = 0
            key = [block, 'disposable', i, 0]
            row = dict(key=key, block=block, history='disposable', current_pass=current, rule=1 if i % 2 else -1,
                selection_hash=hashlib.sha256(str(key).encode()).hexdigest(),
                packet_sha256=hashlib.sha256(packet.tobytes()).hexdigest())
            rows.append(row); packets.append(packet)
            for regime in REGIMES:
                probabilities = dict(tt008=0. if i == 0 else 1., direct_rival=.5, candidate=.75)
                forecasts.append(dict(**row, regime=regime, probabilities=probabilities))
                # Three-record block: one rescue in the singleton failing class;
                # four-record block: one harm in the two-record failing class.
                control = int(i == 0 and block == -1)
                repaired = int(i == 0 and block == -2)
                outcomes.append(dict(key=key, regime=regime, control=control, repaired=repaired))
    return rows, forecasts, outcomes, np.stack(packets)
