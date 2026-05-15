"""Default BPMN discovery JSON shape (Redis + DB)."""

from __future__ import annotations

import copy
import json
from typing import Any

PHASE_DISCOVERY = "discovery"
PHASE_DEEPDIVE = "deepdive"
PHASE_ROUNDUP = "roundup"

PROCESS_PHASE_STEPS = "steps"
PROCESS_PHASE_EXCEPTIONS = "exceptions"


def default_process_detail() -> dict[str, Any]:
    return {
        "phase": PROCESS_PHASE_STEPS,
        "steps": [],
        "exceptions": [],
        "is_completed": False,
    }


DEFAULT_BPMN_STATE: dict[str, Any] = {
    "meta": {
        "phase": PHASE_DISCOVERY,
        "current_focus_process": None,
        "tangent_to_acknowledge": None,
    },
    "discovery": {
        "interviewee_role": "",
        "identified_main_processes": [],
        "is_completed": False,
    },
    "process_details": {},
}


def state_to_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False)


def parse_state_json(raw: str | None) -> dict[str, Any]:
    if not (raw or "").strip():
        return copy.deepcopy(DEFAULT_BPMN_STATE)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return copy.deepcopy(DEFAULT_BPMN_STATE)
    if not isinstance(data, dict):
        return copy.deepcopy(DEFAULT_BPMN_STATE)
    return normalize_state(data)


def meta_phase(state: dict[str, Any]) -> str:
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    phase = meta.get("phase") or meta.get("current_stage") or PHASE_DISCOVERY
    p = str(phase).strip().lower()
    if p in (PHASE_DISCOVERY, PHASE_DEEPDIVE, PHASE_ROUNDUP):
        return p
    if p == "round_up":
        return PHASE_ROUNDUP
    return PHASE_DISCOVERY


def discovery_process_names(state: dict[str, Any]) -> list[str]:
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    procs = discovery.get("identified_main_processes")
    if not isinstance(procs, list):
        return []
    return [str(p).strip() for p in procs if isinstance(p, str) and str(p).strip()]


def normalize_state(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure required top-level keys exist; fill from defaults without clobbering extra keys."""
    out = copy.deepcopy(DEFAULT_BPMN_STATE)
    raw_meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    out["meta"] = {**out["meta"], **raw_meta}
    if not isinstance(out["meta"], dict):
        out["meta"] = copy.deepcopy(DEFAULT_BPMN_STATE["meta"])

    # Legacy: current_stage → phase (incoming current_stage wins over default phase)
    legacy_stage = raw_meta.get("current_stage") or out["meta"].get("current_stage")
    if legacy_stage and not raw_meta.get("phase"):
        out["meta"]["phase"] = legacy_stage
    out["meta"]["phase"] = meta_phase({"meta": out["meta"]})
    out["meta"].pop("current_stage", None)

    out["discovery"] = {**out["discovery"], **(data.get("discovery") or {})}
    if not isinstance(out["discovery"], dict):
        out["discovery"] = copy.deepcopy(DEFAULT_BPMN_STATE["discovery"])

    imp = out["discovery"].get("identified_main_processes")
    if isinstance(imp, list):
        out["discovery"]["identified_main_processes"] = discovery_process_names(
            {"discovery": out["discovery"]}
        )
    else:
        out["discovery"]["identified_main_processes"] = []

    if not isinstance(out["discovery"].get("is_completed"), bool):
        out["discovery"]["is_completed"] = bool(out["discovery"].get("is_completed"))

    pd_in = data.get("process_details")
    pd: dict[str, Any] = pd_in if isinstance(pd_in, dict) else {}
    normalized_pd: dict[str, Any] = {}
    for key, proc in pd.items():
        if not isinstance(key, str) or not key.strip():
            continue
        name = key.strip()
        normalized_pd[name] = _normalize_process_detail(proc if isinstance(proc, dict) else {})

    phase = meta_phase({"meta": out["meta"]})
    if phase in (PHASE_DEEPDIVE, PHASE_ROUNDUP):
        for name in out["discovery"]["identified_main_processes"]:
            if name not in normalized_pd:
                normalized_pd[name] = default_process_detail()
            else:
                normalized_pd[name] = _normalize_process_detail(normalized_pd[name])

    out["process_details"] = normalized_pd

    out = enforce_focus_integrity(out)

    return out


def _normalize_process_detail(proc: dict[str, Any]) -> dict[str, Any]:
    out = default_process_detail()
    out.update(proc)
    if out.get("is_process_fully_mapped") and not out.get("is_completed"):
        out["is_completed"] = bool(out["is_process_fully_mapped"])
    out.pop("is_process_fully_mapped", None)
    if not isinstance(out.get("is_completed"), bool):
        out["is_completed"] = False
    internal = str(out.get("phase") or PROCESS_PHASE_STEPS).strip().lower()
    if internal in ("deepdive", "mapping", PROCESS_PHASE_STEPS):
        out["phase"] = PROCESS_PHASE_STEPS
    elif internal == PROCESS_PHASE_EXCEPTIONS:
        out["phase"] = PROCESS_PHASE_EXCEPTIONS
    else:
        out["phase"] = PROCESS_PHASE_STEPS
    steps = out.get("steps")
    out["steps"] = steps if isinstance(steps, list) else []
    exc = out.get("exceptions")
    out["exceptions"] = exc if isinstance(exc, list) else []
    return out


def enforce_focus_integrity(state: dict[str, Any]) -> dict[str, Any]:
    """
    After tracker output: focus must be an incomplete process only; never revisit completed ones.
    """
    out = copy.deepcopy(state)
    phase = meta_phase(out)
    pd = out.get("process_details") if isinstance(out.get("process_details"), dict) else {}

    if phase == PHASE_ROUNDUP:
        if not all_processes_completed(out):
            out["meta"]["phase"] = PHASE_DEEPDIVE
        else:
            out["meta"]["current_focus_process"] = None
            return out

    if phase != PHASE_DEEPDIVE:
        return out

    names = discovery_process_names(out)
    incomplete = [
        n
        for n in names
        if not (isinstance(pd.get(n), dict) and pd.get(n, {}).get("is_completed"))
    ]

    if not incomplete:
        if names:
            out["meta"]["phase"] = PHASE_ROUNDUP
        out["meta"]["current_focus_process"] = None
        return out

    focus = out["meta"].get("current_focus_process")
    focus_str = focus.strip() if isinstance(focus, str) else None
    if not focus_str or focus_str not in incomplete:
        out["meta"]["current_focus_process"] = incomplete[0]

    return out


def first_incomplete_process_name(state: dict[str, Any]) -> str | None:
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    for name in discovery_process_names(state):
        proc = pd.get(name)
        if not isinstance(proc, dict):
            return name
        if not proc.get("is_completed"):
            return name
    return None


def all_processes_completed(state: dict[str, Any]) -> bool:
    names = discovery_process_names(state)
    if not names:
        return False
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    for name in names:
        proc = pd.get(name)
        if not isinstance(proc, dict) or not proc.get("is_completed"):
            return False
    return True


def deepdive_progress(state: dict[str, Any]) -> dict[str, Any]:
    """Summary for the interviewer: which processes are done vs still to explore."""
    names = discovery_process_names(state)
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    completed: list[str] = []
    remaining: list[str] = []
    for name in names:
        proc = pd.get(name)
        if isinstance(proc, dict) and proc.get("is_completed"):
            completed.append(name)
        else:
            remaining.append(name)
    current = first_incomplete_process_name(state)
    position = ""
    if current and current in names:
        position = f"{names.index(current) + 1} of {len(names)}"
    return {
        "all_processes": names,
        "completed_processes": completed,
        "remaining_processes": remaining,
        "current_process": current,
        "position": position,
    }
