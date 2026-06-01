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
PROCESS_PHASE_CONFIRM = "confirm"

# All must be non-empty before a step is considered mapped or before advancing.
STEP_REQUIRED_FIELDS: tuple[str, ...] = (
    "step_name",
    "tools_software_used",
    "time_taken",
    "handoff_to_next_actor",
)

STEP_FIELD_GAP_PROMPTS: dict[str, str] = {
    "step_name": "Ask what they would call this step in the workflow.",
    "tools_software_used": "Ask which tools or software they use for this step.",
    "time_taken": "Ask roughly how long this step takes when things go smoothly.",
    "handoff_to_next_actor": "Ask who they hand this off to next, or if it stays with them.",
}

EXCEPTION_REQUIRED_FIELDS: tuple[str, ...] = (
    "what_goes_wrong",
    "impact",
    "recovery",
)

EXCEPTION_FIELD_GAP_PROMPTS: dict[str, str] = {
    "what_goes_wrong": "Ask what typically goes wrong or where things get stuck in this process.",
    "impact": "Ask how often that happens and what impact it has on their work.",
    "recovery": "Ask how they usually recover or fix it when that happens.",
}


def default_step() -> dict[str, Any]:
    return {
        "step_name": "",
        "tools_software_used": "",
        "time_taken": "",
        "handoff_to_next_actor": "",
        "comments_to_explore": "",
        "is_mapped": False,
    }


def default_exception() -> dict[str, Any]:
    return {
        "what_goes_wrong": "",
        "impact": "",
        "recovery": "",
        "comments_to_explore": "",
        "is_mapped": False,
    }


def default_process_detail() -> dict[str, Any]:
    return {
        "phase": PROCESS_PHASE_STEPS,
        "steps": [],
        "exceptions": [],
        "summary_confirmed": False,
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

    out = enforce_steps_on_state(out)
    out = enforce_phase_transitions(out)
    out = enforce_focus_integrity(out)

    return out


def enforce_phase_transitions(state: dict[str, Any]) -> dict[str, Any]:
    """Keep meta.phase aligned with discovery / process completion gates."""
    out = copy.deepcopy(state)
    discovery = out.get("discovery") if isinstance(out.get("discovery"), dict) else {}
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    names = discovery_process_names(out)

    if bool(discovery.get("is_completed")) and names and meta_phase(out) == PHASE_DISCOVERY:
        out.setdefault("meta", {})["phase"] = PHASE_DEEPDIVE

    if names and all_processes_completed(out):
        out.setdefault("meta", {})["phase"] = PHASE_ROUNDUP
        out["meta"]["current_focus_process"] = None

    return out


def process_deepdive_subphase(proc: dict[str, Any]) -> str:
    if not isinstance(proc, dict):
        return PROCESS_PHASE_STEPS
    internal = str(proc.get("phase") or PROCESS_PHASE_STEPS).strip().lower()
    if internal == PROCESS_PHASE_EXCEPTIONS:
        return PROCESS_PHASE_EXCEPTIONS
    if internal == PROCESS_PHASE_CONFIRM:
        return PROCESS_PHASE_CONFIRM
    return PROCESS_PHASE_STEPS


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
    elif internal == PROCESS_PHASE_CONFIRM:
        out["phase"] = PROCESS_PHASE_CONFIRM
    else:
        out["phase"] = PROCESS_PHASE_STEPS
    if not isinstance(out.get("summary_confirmed"), bool):
        if out.get("is_completed"):
            out["summary_confirmed"] = True
        else:
            out["summary_confirmed"] = False
    steps = out.get("steps")
    normalized_steps: list[dict[str, Any]] = []
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict):
                normalized_steps.append(_normalize_step(s))
    out["steps"] = normalized_steps
    exc = out.get("exceptions")
    normalized_exceptions: list[dict[str, Any]] = []
    if isinstance(exc, list):
        for item in exc:
            if isinstance(item, dict):
                normalized_exceptions.append(_normalize_exception(item))
            elif isinstance(item, str) and item.strip():
                normalized_exceptions.append(
                    _normalize_exception({"what_goes_wrong": item.strip()})
                )
    out["exceptions"] = normalized_exceptions
    return out


def _normalize_exception(exc: dict[str, Any]) -> dict[str, Any]:
    out = default_exception()
    out.update(exc)
    if not isinstance(out.get("is_mapped"), bool):
        out["is_mapped"] = False
    for key in (*EXCEPTION_REQUIRED_FIELDS, "comments_to_explore"):
        if not isinstance(out.get(key), str):
            out[key] = str(out.get(key) or "")
    if out.get("is_mapped") and not exception_is_fully_mapped(out):
        out["is_mapped"] = False
    return out


def _normalize_step(step: dict[str, Any]) -> dict[str, Any]:
    out = default_step()
    out.update(step)
    legacy_complete = out.pop("is_step_complete", None)  # legacy
    if legacy_complete and not out.get("is_mapped"):
        out["is_mapped"] = bool(legacy_complete)
    if not isinstance(out.get("is_mapped"), bool):
        out["is_mapped"] = False
    for key in (*STEP_REQUIRED_FIELDS, "comments_to_explore"):
        if not isinstance(out.get(key), str):
            out[key] = str(out.get(key) or "")
    if out.get("is_mapped") and not step_is_fully_mapped(out):
        out["is_mapped"] = False
    return out


def step_missing_fields(step: dict[str, Any]) -> list[str]:
    return [f for f in STEP_REQUIRED_FIELDS if not (step.get(f) or "").strip()]


def step_is_fully_mapped(step: dict[str, Any]) -> bool:
    return len(step_missing_fields(step)) == 0


def step_gap_comment(step: dict[str, Any]) -> str:
    """One concrete interviewer prompt for the first missing required field."""
    missing = step_missing_fields(step)
    if not missing:
        return ""
    return STEP_FIELD_GAP_PROMPTS.get(missing[0], f"Ask about {missing[0]}.")


def all_steps_fully_mapped(proc: dict[str, Any]) -> bool:
    steps = proc.get("steps")
    if not isinstance(steps, list) or not steps:
        return False
    for s in steps:
        if not isinstance(s, dict):
            return False
        if not step_is_fully_mapped(_normalize_step(s)):
            return False
    return True


def exception_missing_fields(exc: dict[str, Any]) -> list[str]:
    return [f for f in EXCEPTION_REQUIRED_FIELDS if not (exc.get(f) or "").strip()]


def exception_is_fully_mapped(exc: dict[str, Any]) -> bool:
    return len(exception_missing_fields(exc)) == 0


def exception_gap_comment(exc: dict[str, Any]) -> str:
    missing = exception_missing_fields(exc)
    if not missing:
        return ""
    return EXCEPTION_FIELD_GAP_PROMPTS.get(missing[0], f"Ask about {missing[0]}.")


def all_exceptions_fully_mapped(proc: dict[str, Any]) -> bool:
    excs = proc.get("exceptions")
    if not isinstance(excs, list) or not excs:
        return False
    for item in excs:
        if not isinstance(item, dict):
            return False
        if not exception_is_fully_mapped(_normalize_exception(item)):
            return False
    return True


def process_ready_for_exceptions(proc: dict[str, Any]) -> bool:
    return all_steps_fully_mapped(proc)


def process_ready_for_confirm(proc: dict[str, Any]) -> bool:
    return process_ready_for_exceptions(proc) and all_exceptions_fully_mapped(proc)


def process_fully_complete(proc: dict[str, Any]) -> bool:
    if not isinstance(proc, dict):
        return False
    if not proc.get("summary_confirmed") or not proc.get("is_completed"):
        return False
    return process_ready_for_confirm(proc)


def enforce_process_steps(proc: dict[str, Any]) -> dict[str, Any]:
    """Ensure steps/exceptions mapping, phase gates, and summary confirmation."""
    out = _normalize_process_detail(proc if isinstance(proc, dict) else {})
    steps_in = out.get("steps")
    if not isinstance(steps_in, list):
        out["steps"] = []

    normalized_steps: list[dict[str, Any]] = []
    step_focus_idx: int | None = None
    for s in steps_in if isinstance(steps_in, list) else []:
        if not isinstance(s, dict):
            continue
        step = _normalize_step(s)
        if not step_is_fully_mapped(step):
            step["is_mapped"] = False
            if step_focus_idx is None:
                step_focus_idx = len(normalized_steps)
                step["comments_to_explore"] = step_gap_comment(step)
            else:
                step["comments_to_explore"] = ""
        else:
            step["is_mapped"] = True
            step["comments_to_explore"] = ""
        normalized_steps.append(step)
    out["steps"] = normalized_steps

    if process_ready_for_exceptions(out) and out.get("phase") == PROCESS_PHASE_STEPS:
        out["phase"] = PROCESS_PHASE_EXCEPTIONS

    exc_in = out.get("exceptions")
    if not isinstance(exc_in, list):
        exc_in = []
    if out.get("phase") == PROCESS_PHASE_EXCEPTIONS and process_ready_for_exceptions(out):
        if not exc_in:
            exc_in = [default_exception()]

    # Never stay in exceptions / confirm while steps are still incomplete.
    if out.get("phase") in (PROCESS_PHASE_EXCEPTIONS, PROCESS_PHASE_CONFIRM):
        if not process_ready_for_exceptions(out):
            out["phase"] = PROCESS_PHASE_STEPS

    normalized_exceptions: list[dict[str, Any]] = []
    exc_focus_idx: int | None = None
    for item in exc_in:
        if isinstance(item, dict):
            exc = _normalize_exception(item)
        elif isinstance(item, str) and item.strip():
            exc = _normalize_exception({"what_goes_wrong": item.strip()})
        else:
            continue
        if not exception_is_fully_mapped(exc):
            exc["is_mapped"] = False
            if exc_focus_idx is None:
                exc_focus_idx = len(normalized_exceptions)
                exc["comments_to_explore"] = exception_gap_comment(exc)
            else:
                exc["comments_to_explore"] = ""
        else:
            exc["is_mapped"] = True
            exc["comments_to_explore"] = ""
        normalized_exceptions.append(exc)
    out["exceptions"] = normalized_exceptions

    if out.get("phase") == PROCESS_PHASE_EXCEPTIONS and not process_ready_for_exceptions(out):
        out["phase"] = PROCESS_PHASE_STEPS

    if process_ready_for_confirm(out) and not out.get("summary_confirmed"):
        out["phase"] = PROCESS_PHASE_CONFIRM
    elif out.get("phase") == PROCESS_PHASE_CONFIRM and not process_ready_for_confirm(out):
        out["phase"] = (
            PROCESS_PHASE_EXCEPTIONS
            if process_ready_for_exceptions(out)
            else PROCESS_PHASE_STEPS
        )

    if out.get("is_completed") and not process_fully_complete(out):
        out["is_completed"] = False

    # Tracker sometimes sets summary_confirmed after a conversational "you got it" without
    # full step/exception mapping — keep state and directives aligned with real gaps.
    if out.get("summary_confirmed") and not process_ready_for_confirm(out):
        out["summary_confirmed"] = False

    if out.get("summary_confirmed") and process_ready_for_confirm(out):
        out["is_completed"] = True

    return out


def enforce_steps_on_state(state: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(state)
    pd = out.get("process_details")
    if not isinstance(pd, dict):
        return out
    for key, proc in list(pd.items()):
        if isinstance(proc, dict):
            pd[key] = enforce_process_steps(proc)
    out["process_details"] = pd
    return out


def first_active_exception(proc: dict[str, Any]) -> tuple[dict[str, Any] | None, int | None]:
    excs = proc.get("exceptions")
    if not isinstance(excs, list):
        return None, None
    for i, item in enumerate(excs):
        if not isinstance(item, dict):
            continue
        exc = _normalize_exception(item)
        if not exception_is_fully_mapped(exc):
            return exc, i
    return None, None


def exception_mapping_progress(proc: dict[str, Any]) -> dict[str, Any]:
    excs = proc.get("exceptions") if isinstance(proc.get("exceptions"), list) else []
    labels: list[str] = []
    mapped: list[str] = []
    for item in excs:
        if not isinstance(item, dict):
            continue
        exc = _normalize_exception(item)
        label = (exc.get("what_goes_wrong") or "").strip() or "unnamed issue"
        labels.append(label)
        if exception_is_fully_mapped(exc):
            mapped.append(label)
    current_exc, idx = first_active_exception(proc if isinstance(proc, dict) else {})
    current_label = (
        (current_exc.get("what_goes_wrong") or "").strip() if current_exc else None
    ) or None
    position = ""
    if current_label and current_label in labels:
        position = f"{labels.index(current_label) + 1} of {len(labels)}"
    elif idx is not None and labels:
        position = f"{idx + 1} of {len(labels)}"
    return {
        "all_exceptions": labels,
        "mapped_exceptions": mapped,
        "current_exception": current_label,
        "position": position,
    }


def first_active_step(proc: dict[str, Any]) -> tuple[dict[str, Any] | None, int | None]:
    """First step that does not yet have all required fields filled."""
    steps = proc.get("steps")
    if not isinstance(steps, list):
        return None, None
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            continue
        step = _normalize_step(s)
        if not step_is_fully_mapped(step):
            return step, i
    return None, None


def step_mapping_progress(proc: dict[str, Any]) -> dict[str, Any]:
    steps = proc.get("steps") if isinstance(proc.get("steps"), list) else []
    names: list[str] = []
    mapped: list[str] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        step = _normalize_step(s)
        name = (step.get("step_name") or "").strip() or "unnamed step"
        names.append(name)
        if step_is_fully_mapped(step):
            mapped.append(name)
    current_step, idx = first_active_step(proc if isinstance(proc, dict) else {})
    current_name = (current_step.get("step_name") or "").strip() if current_step else None
    position = ""
    if current_name and current_name in names:
        position = f"{names.index(current_name) + 1} of {len(names)}"
    elif idx is not None and names:
        position = f"{idx + 1} of {len(names)}"
    return {
        "all_steps": names,
        "mapped_steps": mapped,
        "current_step": current_name,
        "position": position,
    }


def process_summary_for_interviewer(proc: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(proc, dict):
        proc = {}
    subphase = process_deepdive_subphase(proc)
    steps = proc.get("steps") if isinstance(proc.get("steps"), list) else []
    excs = proc.get("exceptions") if isinstance(proc.get("exceptions"), list) else []
    steps_done = all_steps_fully_mapped(proc) if steps else False
    excs_done = all_exceptions_fully_mapped(proc) if excs else False
    return {
        "deepdive_subphase": subphase,
        "deepdive_subphase_label": (
            "1 of 2 — walk through each step"
            if subphase == PROCESS_PHASE_STEPS
            else "2 of 2 — what goes wrong (exceptions)"
            if subphase == PROCESS_PHASE_EXCEPTIONS
            else "confirm your understanding"
        ),
        "phase": proc.get("phase") or PROCESS_PHASE_STEPS,
        "steps_complete": steps_done,
        "exceptions_complete": excs_done,
        "is_completed": bool(proc.get("is_completed")),
        "summary_confirmed": bool(proc.get("summary_confirmed")),
    }


def incomplete_process_names(state: dict[str, Any]) -> list[str]:
    """Processes not yet fully mapped (steps + exceptions), in discovery list order."""
    names = discovery_process_names(state)
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    out: list[str] = []
    for name in names:
        proc = pd.get(name)
        if not isinstance(proc, dict) or not process_fully_complete(proc):
            out.append(name)
    return out


def completed_process_names(state: dict[str, Any]) -> list[str]:
    names = discovery_process_names(state)
    incomplete = set(incomplete_process_names(state))
    return [n for n in names if n not in incomplete]


def resolve_focus_process_name(
    state: dict[str, Any],
    *,
    prefer_tracker_focus: bool = True,
) -> str | None:
    """
    Pick the process the interviewer should work on now.
    Never returns a fully completed process. When most processes are already done
    (typical after roundup adds a new task), prefer the last incomplete in list order
    so we skip back to earlier items.
    """
    incomplete = incomplete_process_names(state)
    if not incomplete:
        return None

    if prefer_tracker_focus:
        meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
        focus = meta.get("current_focus_process")
        focus_str = focus.strip() if isinstance(focus, str) else None
        if focus_str and focus_str in incomplete:
            return focus_str

    names = discovery_process_names(state)
    completed_count = len(names) - len(incomplete)
    if completed_count > 0 and len(incomplete) <= completed_count:
        for name in reversed(names):
            if name in incomplete:
                return name
    return incomplete[0]


def preserve_completed_processes(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """
    After tracker merge: never let a fully mapped process be wiped or reopened
    because a new process was added during roundup.
    """
    out = copy.deepcopy(after)
    before_pd = before.get("process_details")
    after_pd = out.get("process_details")
    if not isinstance(before_pd, dict) or not isinstance(after_pd, dict):
        return out

    for name, prev_proc in before_pd.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(prev_proc, dict) or not process_fully_complete(prev_proc):
            continue
        new_proc = after_pd.get(name)
        if isinstance(new_proc, dict) and process_fully_complete(new_proc):
            continue
        after_pd[name] = copy.deepcopy(prev_proc)

    out["process_details"] = after_pd
    return out


def enforce_focus_integrity(state: dict[str, Any]) -> dict[str, Any]:
    """
    After tracker output: focus must be an incomplete process only; never revisit completed ones.
    """
    out = copy.deepcopy(state)
    phase = meta_phase(out)

    if phase == PHASE_ROUNDUP:
        if all_processes_completed(out):
            out["meta"]["current_focus_process"] = None
            return out
        out["meta"]["phase"] = PHASE_DEEPDIVE

    if meta_phase(out) != PHASE_DEEPDIVE:
        return out

    names = discovery_process_names(out)
    incomplete = incomplete_process_names(out)

    if not incomplete:
        if names:
            out["meta"]["phase"] = PHASE_ROUNDUP
        out["meta"]["current_focus_process"] = None
        return out

    target = resolve_focus_process_name(out, prefer_tracker_focus=True)
    if target:
        out["meta"]["current_focus_process"] = target
    else:
        out["meta"]["current_focus_process"] = incomplete[0]

    return out


def first_incomplete_process_name(state: dict[str, Any]) -> str | None:
    """Alias for resolve_focus_process_name (respects meta.current_focus_process when valid)."""
    return resolve_focus_process_name(state, prefer_tracker_focus=True)


def all_processes_completed(state: dict[str, Any]) -> bool:
    names = discovery_process_names(state)
    if not names:
        return False
    pd = state.get("process_details") if isinstance(state.get("process_details"), dict) else {}
    for name in names:
        proc = pd.get(name)
        if not isinstance(proc, dict) or not process_fully_complete(proc):
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
        if isinstance(proc, dict) and process_fully_complete(proc):
            completed.append(name)
        else:
            remaining.append(name)
    current = resolve_focus_process_name(state, prefer_tracker_focus=True)
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
