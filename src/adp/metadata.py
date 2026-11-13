"""Dataset specs: the metadata that drives ingestion (docs/contracts-adp.md).

One YAML file per dataset under config/adp/datasets/. Loading validates the
spec and fails loudly on anything the ingestion engine would otherwise have to
guess about, so a typo never becomes a silently skipped column.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

TYPES = {"int", "decimal", "date", "timestamp", "enum", "bool", "string"}
MODES = {"incremental", "full"}
DELETION = {"tombstone", "none"}


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    required: bool
    values: tuple = ()
    scale: int = 2


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    contract_version: str
    source_type: str
    source_table: str
    mode: str
    cursor_column: str
    primary_key: tuple
    lookback_hours: int
    deletion_strategy: str
    max_quarantine_ratio: float
    bronze_name: str
    columns: dict  # name -> Column, in contract order

    @property
    def required_columns(self):
        return [c for c in self.columns.values() if c.required]


def _need(raw, key, where):
    if key not in raw:
        raise SpecError(f"{where}: missing '{key}'")
    return raw[key]


def parse_spec(raw, where="spec"):
    src, ing, tgt = (_need(raw, k, where) for k in ("source", "ingestion", "target"))
    cols_raw = _need(raw, "columns", where)
    columns = {}
    for name, c in cols_raw.items():
        kind = _need(c, "type", f"{where}.columns.{name}")
        if kind not in TYPES:
            raise SpecError(f"{where}.columns.{name}: unknown type '{kind}'")
        if kind == "enum" and not c.get("values"):
            raise SpecError(f"{where}.columns.{name}: enum needs values")
        columns[name] = Column(name, kind, bool(c.get("required", False)),
                               tuple(c.get("values", ())), int(c.get("scale", 2)))

    spec = DatasetSpec(
        dataset_id=_need(raw, "dataset_id", where),
        contract_version=_need(raw, "contract_version", where),
        source_type=_need(src, "type", where),
        source_table=_need(src, "table", where),
        mode=_need(ing, "mode", where),
        cursor_column=_need(ing, "cursor_column", where),
        primary_key=tuple(_need(ing, "primary_key", where)),
        lookback_hours=int(ing.get("lookback_hours", 0)),
        deletion_strategy=ing.get("deletion_strategy", "none"),
        max_quarantine_ratio=float(ing.get("max_quarantine_ratio", 0.0)),
        bronze_name=_need(tgt, "bronze_name", where),
        columns=columns,
    )
    if spec.mode not in MODES:
        raise SpecError(f"{where}: mode must be one of {sorted(MODES)}")
    if spec.deletion_strategy not in DELETION:
        raise SpecError(f"{where}: deletion_strategy must be one of {sorted(DELETION)}")
    for key in spec.primary_key + (spec.cursor_column,):
        if key not in columns or not columns[key].required:
            raise SpecError(f"{where}: '{key}' must be a required column")
    if columns[spec.cursor_column].type != "timestamp":
        raise SpecError(f"{where}: cursor column must be a timestamp")
    if not 0.0 <= spec.max_quarantine_ratio < 1.0:
        raise SpecError(f"{where}: max_quarantine_ratio must be in [0, 1)")
    return spec


def load_specs(directory):
    """Return {dataset_id: DatasetSpec} for every *.yml in `directory`."""
    specs = {}
    for path in sorted(Path(directory).glob("*.yml")):
        spec = parse_spec(yaml.safe_load(path.read_text()), where=path.name)
        if spec.dataset_id in specs:
            raise SpecError(f"{path.name}: duplicate dataset_id {spec.dataset_id}")
        specs[spec.dataset_id] = spec
    if not specs:
        raise SpecError(f"no dataset specs in {directory}")
    return specs


DEFAULT_DIR = Path(__file__).resolve().parents[2] / "config" / "adp" / "datasets"
