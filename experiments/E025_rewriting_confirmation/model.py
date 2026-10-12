"""Exact E024 numerical apparatus, reused for a fresh inferential confirmation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from E024_serial_compensation import model as predecessor

renewal = predecessor.renewal
base, acquisition = predecessor.base, predecessor.acquisition
CFG, Cycle, CYCLE = predecessor.CFG, predecessor.Cycle, predecessor.CYCLE
PORTS, RULES, CUES = predecessor.PORTS.copy(), predecessor.RULES.copy(), predecessor.CUES.copy()
ARMS, DAMAGE = predecessor.ARMS, predecessor.DAMAGE
CONDITIONS, ACTIVE, READER_MODES = predecessor.CONDITIONS, predecessor.ACTIVE, predecessor.READER_MODES
RECEIVERS, HORIZONS, PANELS = predecessor.RECEIVERS, predecessor.HORIZONS, predecessor.PANELS
receiver_denominators = predecessor.receiver_denominators
replace_record = predecessor.replace_record
assay = predecessor.assay
score = predecessor.score
