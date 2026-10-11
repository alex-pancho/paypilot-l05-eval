""
import hashlib
import json
from pathlib import Path

from assertions import NAME_TO_LEVEL

REQUIRED = ("id",)
REQUIRED_META = ("layer", "oracle", "assertion", "severity", "source")
LAYERS = {"generation", "retrieval", "memory", "action", "judge", "orchestration"}
ORACLES = {"engine", "corpus", "human"}
SEVERITIES = {"low", "medium", "high", "critical"}
GATES = {"daily", "release"}


class SetError(ValueError):
    pass


def load(path: str | Path) -> list[dict]:
    ""
    path = Path(path)
    if not path.exists():
        raise SetError(f"set not found: {path}")
    cases, seen = [], set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as e:
            raise SetError(f"{path.name}:{lineno}: bad JSON — {e}") from e
        _validate(case, f"{path.name}:{lineno}")
        if case["id"] in seen:
            raise SetError(f"{path.name}:{lineno}: duplicate id {case['id']}")
        seen.add(case["id"])
        cases.append(case)
    if not cases:
        raise SetError(f"{path.name}: no cases")
    return cases


def _validate(case: dict, where: str) -> None:
    for key in REQUIRED:
        if not case.get(key):
            raise SetError(f"{where}: missing {key}")
    if not case.get("input") and not case.get("turns"):
        raise SetError(f"{where}: needs either input or turns")
    meta = case.get("additional_metadata") or {}
    for key in REQUIRED_META:
        if not meta.get(key):
            raise SetError(f"{where}: additional_metadata.{key} is required")
    if meta["layer"] not in LAYERS:
        raise SetError(f"{where}: unknown layer {meta['layer']!r}")
    if meta["oracle"] not in ORACLES:
        raise SetError(f"{where}: unknown oracle {meta['oracle']!r}")
    if meta["severity"] not in SEVERITIES:
        raise SetError(f"{where}: unknown severity {meta['severity']!r}")
    if meta["assertion"] not in NAME_TO_LEVEL:
        raise SetError(f"{where}: unknown assertion {meta['assertion']!r}")
    if meta.get("gate") and meta["gate"] not in GATES:
        raise SetError(f"{where}: unknown gate {meta['gate']!r}")
    if meta["layer"] == "retrieval" and not meta.get("reference"):
        raise SetError(f"{where}: retrieval cases need a reference "
                       "(context recall cannot be computed without it)")
    if case.get("turns"):
        for t in case["turns"]:
            if t.get("role") not in ("user", "assistant"):
                raise SetError(f"{where}: bad turn role {t.get('role')!r}")
    if meta["assertion"] == "dialog":
        _validate_dialog(case, meta, where)
    if "summarize_after" in meta and not (
            isinstance(meta["summarize_after"], int) and meta["summarize_after"] > 0):
        raise SetError(f"{where}: summarize_after must be a positive integer")


def _validate_dialog(case: dict, meta: dict, where: str) -> None:
    ""
    if not case.get("turns"):
        raise SetError(f"{where}: assertion 'dialog' needs turns")
    n_user = sum(1 for t in case["turns"] if t["role"] == "user")
    checks = meta.get("checks")
    if not checks:
        raise SetError(f"{where}: assertion 'dialog' needs additional_metadata.checks")
    if all(c.get("precondition") for c in checks):
        raise SetError(f"{where}: a dialog needs at least one check that is "
                       "not a precondition")
    for i, c in enumerate(checks, 1):
        at = f"{where}: checks[{i}]"
        if c.get("assertion") not in NAME_TO_LEVEL or c["assertion"] == "dialog":
            raise SetError(f"{at}: unknown assertion {c.get('assertion')!r}")
        turns = c.get("turns") or ([c["turn"]] if c.get("turn") else [])
        if not turns:
            raise SetError(f"{at}: needs turn (1-based) or turns")
        for t in turns:
            if not isinstance(t, int) or not 1 <= t <= n_user:
                raise SetError(f"{at}: turn {t!r} is outside 1..{n_user} "
                               "(user turns are counted)")


def set_hash(path: str | Path) -> str:
    ""
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]


def summarise(cases: list[dict]) -> dict:
    ""
    meta = [c.get("additional_metadata", {}) for c in cases]
    levels = set()
    for m in meta:
        if m["assertion"] == "dialog":
            levels |= {NAME_TO_LEVEL[c["assertion"]] for c in m["checks"]
                       if not c.get("precondition")}
        else:
            levels.add(NAME_TO_LEVEL[m["assertion"]])
    return {
        "cases": len(cases),
        "multi_turn": sum(1 for c in cases if c.get("turns")),
        "layers": _count(m["layer"] for m in meta),
        "oracles": _count(m["oracle"] for m in meta),
        "sources": _count(m["source"] for m in meta),
        "severities": _count(m["severity"] for m in meta),
        "ladder_levels": sorted(levels),
        "gates": _count(m.get("gate", "-") for m in meta),
        "human_oracle_pct": round(
            100 * sum(1 for m in meta if m["oracle"] == "human") / len(meta), 1),
        "severity_filled_pct": round(
            100 * sum(1 for m in meta if m.get("severity")) / len(meta), 1),
    }


def _count(values) -> dict:
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))
