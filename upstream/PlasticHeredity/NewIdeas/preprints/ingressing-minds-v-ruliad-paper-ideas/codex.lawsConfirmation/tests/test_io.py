from pathlib import Path

import pytest

from laws_confirmation.io import external_root, require_beneath


def test_external_root_rejects_non_bioice_path():
    with pytest.raises(ValueError):
        external_root("/tmp/not-the-data-disk")


def test_require_beneath_rejects_escape():
    root = Path("/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation")
    assert require_beneath(root / "outputs/test", root) == (root / "outputs/test").resolve()
    with pytest.raises(ValueError):
        require_beneath(root / "../escape", root)

