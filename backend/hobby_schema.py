"""Default hobby discovery JSON shape (Redis + DB)."""

from __future__ import annotations

import copy
import json
from typing import Any

PHASE_DISCOVERY = "discovery"
PHASE_DEEPDIVE = "deepdive"
PHASE_ROUNDUP = "roundup"

# Filled one at a time during deep dive (order guides gap prompts).
HOBBY_REQUIRED_FIELDS: tuple[str, ...] = (
    "description",
    "location",
    "frequency",
    "participants",
    "cost",
)

HOBBY_FIELD_GAP_PROMPTS: dict[str, str] = {
    "description": (
        "Ask in full sentences what they actually do in this hobby and what they enjoy about it — "
        "not a one-word prompt."
    ),
    "location": (
        "Ask where they usually do this hobby (e.g. which club, gym, park, or at home)."
    ),
    "frequency": (
        "Ask how often they practice or do this hobby in a typical week or month."
    ),
    "participants": (
        "Ask who they usually do this with, or whether they mostly do it on their own."
    ),
    "cost": (
        "Ask what it costs them — membership, gear, travel — with rough amounts per month or year."
    ),
}


def default_hobby_detail() -> dict[str, Any]:
    return {
        "location": "",
        "frequency": "",
        "cost": "",
        "description": "",
        "participants": "",
        "comments_to_explore": "",
        "is_completed": False,
    }


DEFAULT_HOBBY_STATE: dict[str, Any] = {
    "meta": {
        "phase": PHASE_DISCOVERY,
        "current_focus_hobby": None,
        "tangent_to_acknowledge": None,
        "favorite_hobby": "",
        "roundup_opening_done": False,
    },
    "discovery": {
        "freetime_context": "",
        "identified_hobbies": [],
        "is_completed": False,
    },
    "hobby_details": {},
}


def state_to_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False)


def _migrate_legacy_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Map legacy BPMN-shaped state into hobby schema."""
    out = copy.deepcopy(data)
    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    discovery = out.get("discovery") if isinstance(out.get("discovery"), dict) else {}

    if "current_focus_hobby" not in meta and meta.get("current_focus_process"):
        meta["current_focus_hobby"] = meta.pop("current_focus_process")
    if "favorite_hobby" not in meta:
        meta["favorite_hobby"] = meta.get("favorite_hobby") or ""
    if "roundup_opening_done" not in meta:
        meta["roundup_opening_done"] = bool(meta.get("roundup_opening_done"))

    if "freetime_context" not in discovery:
        discovery["freetime_context"] = (
            discovery.get("freetime_context")
            or discovery.get("interviewee_role")
            or ""
        )
    if "identified_hobbies" not in discovery:
        legacy = discovery.get("identified_main_processes")
        discovery["identified_hobbies"] = legacy if isinstance(legacy, list) else []

    if "hobby_details" not in out and isinstance(out.get("process_details"), dict):
        hd: dict[str, Any] = {}
        for name, proc in out["process_details"].items():
            if isinstance(name, str) and name.strip() and isinstance(proc, dict):
                hd[name.strip()] = _migrate_legacy_process_detail(proc)
        out["hobby_details"] = hd

    out["meta"] = meta
    out["discovery"] = discovery
    out.pop("process_details", None)
    return out


def _migrate_legacy_process_detail(proc: dict[str, Any]) -> dict[str, Any]:
    detail = default_hobby_detail()
    desc_parts: list[str] = []
    steps = proc.get("steps")
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict) and (s.get("step_name") or "").strip():
                desc_parts.append(str(s["step_name"]).strip())
    if desc_parts:
        detail["description"] = "; ".join(desc_parts)
    loc = (proc.get("location") or "").strip()
    if loc:
        detail["location"] = loc
    if proc.get("is_completed"):
        for f in HOBBY_REQUIRED_FIELDS:
            if not (detail.get(f) or "").strip():
                detail[f] = "unknown"
        detail["is_completed"] = hobby_is_fully_mapped(detail)
    return detail


def parse_state_json(raw: str | None) -> dict[str, Any]:
    if not (raw or "").strip():
        return copy.deepcopy(DEFAULT_HOBBY_STATE)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return copy.deepcopy(DEFAULT_HOBBY_STATE)
    if not isinstance(data, dict):
        return copy.deepcopy(DEFAULT_HOBBY_STATE)
    return normalize_state(_migrate_legacy_keys(data))


def meta_phase(state: dict[str, Any]) -> str:
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    phase = meta.get("phase") or meta.get("current_stage") or PHASE_DISCOVERY
    p = str(phase).strip().lower()
    if p in (PHASE_DISCOVERY, PHASE_DEEPDIVE, PHASE_ROUNDUP):
        return p
    if p == "round_up":
        return PHASE_ROUNDUP
    return PHASE_DISCOVERY


def discovery_hobby_names(state: dict[str, Any]) -> list[str]:
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    hobbies = discovery.get("identified_hobbies")
    if not isinstance(hobbies, list):
        return []
    return [str(h).strip() for h in hobbies if isinstance(h, str) and str(h).strip()]


def normalize_state(data: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULT_HOBBY_STATE)
    raw_meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    out["meta"] = {**out["meta"], **raw_meta}
    if not isinstance(out["meta"], dict):
        out["meta"] = copy.deepcopy(DEFAULT_HOBBY_STATE["meta"])

    legacy_stage = raw_meta.get("current_stage") or out["meta"].get("current_stage")
    if legacy_stage and not raw_meta.get("phase"):
        out["meta"]["phase"] = legacy_stage
    out["meta"]["phase"] = meta_phase({"meta": out["meta"]})
    out["meta"].pop("current_stage", None)
    if not isinstance(out["meta"].get("favorite_hobby"), str):
        out["meta"]["favorite_hobby"] = str(out["meta"].get("favorite_hobby") or "")
    if not isinstance(out["meta"].get("roundup_opening_done"), bool):
        out["meta"]["roundup_opening_done"] = bool(out["meta"].get("roundup_opening_done"))

    out["discovery"] = {**out["discovery"], **(data.get("discovery") or {})}
    if not isinstance(out["discovery"], dict):
        out["discovery"] = copy.deepcopy(DEFAULT_HOBBY_STATE["discovery"])

    out["discovery"]["identified_hobbies"] = discovery_hobby_names({"discovery": out["discovery"]})
    if not isinstance(out["discovery"].get("is_completed"), bool):
        out["discovery"]["is_completed"] = bool(out["discovery"].get("is_completed"))
    if not isinstance(out["discovery"].get("freetime_context"), str):
        out["discovery"]["freetime_context"] = str(out["discovery"].get("freetime_context") or "")

    hd_in = data.get("hobby_details")
    hd: dict[str, Any] = hd_in if isinstance(hd_in, dict) else {}
    normalized_hd: dict[str, Any] = {}
    for key, detail in hd.items():
        if not isinstance(key, str) or not key.strip():
            continue
        normalized_hd[key.strip()] = _normalize_hobby_detail(
            detail if isinstance(detail, dict) else {}
        )

    phase = meta_phase({"meta": out["meta"]})
    if phase in (PHASE_DEEPDIVE, PHASE_ROUNDUP):
        for name in out["discovery"]["identified_hobbies"]:
            if name not in normalized_hd:
                normalized_hd[name] = default_hobby_detail()
            else:
                normalized_hd[name] = _normalize_hobby_detail(normalized_hd[name])

    out["hobby_details"] = normalized_hd
    out = enforce_hobbies_on_state(out)
    out = enforce_phase_transitions(out)
    out = enforce_focus_integrity(out)
    return out


def _normalize_hobby_detail(detail: dict[str, Any]) -> dict[str, Any]:
    out = default_hobby_detail()
    out.update(detail)
    for key in (*HOBBY_REQUIRED_FIELDS, "comments_to_explore"):
        if not isinstance(out.get(key), str):
            out[key] = str(out.get(key) or "")
    if out.get("is_completed") and not hobby_is_fully_mapped(out):
        out["is_completed"] = False
    if hobby_is_fully_mapped(out):
        out["is_completed"] = True
        out["comments_to_explore"] = ""
    return out


def hobby_missing_fields(detail: dict[str, Any]) -> list[str]:
    return [f for f in HOBBY_REQUIRED_FIELDS if not (detail.get(f) or "").strip()]


def hobby_is_fully_mapped(detail: dict[str, Any]) -> bool:
    return len(hobby_missing_fields(detail)) == 0


def hobby_gap_comment(detail: dict[str, Any]) -> str:
    missing = hobby_missing_fields(detail)
    if not missing:
        return ""
    return HOBBY_FIELD_GAP_PROMPTS.get(missing[0], f"Ask about {missing[0]}.")


def hobby_fully_complete(detail: dict[str, Any]) -> bool:
    if not isinstance(detail, dict):
        return False
    return bool(detail.get("is_completed")) and hobby_is_fully_mapped(detail)


def enforce_hobby_detail(detail: dict[str, Any]) -> dict[str, Any]:
    out = _normalize_hobby_detail(detail if isinstance(detail, dict) else {})
    if not hobby_is_fully_mapped(out):
        out["is_completed"] = False
        out["comments_to_explore"] = hobby_gap_comment(out)
    else:
        out["is_completed"] = True
        out["comments_to_explore"] = ""
    return out


def enforce_hobbies_on_state(state: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(state)
    hd = out.get("hobby_details")
    if not isinstance(hd, dict):
        return out
    for key, detail in list(hd.items()):
        if isinstance(detail, dict):
            hd[key] = enforce_hobby_detail(detail)
    out["hobby_details"] = hd
    return out


def enforce_phase_transitions(state: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(state)
    discovery = out.get("discovery") if isinstance(out.get("discovery"), dict) else {}
    names = discovery_hobby_names(out)

    if bool(discovery.get("is_completed")) and names and meta_phase(out) == PHASE_DISCOVERY:
        out.setdefault("meta", {})["phase"] = PHASE_DEEPDIVE

    if names and all_hobbies_completed(out):
        prev_phase = meta_phase(state)
        out.setdefault("meta", {})["phase"] = PHASE_ROUNDUP
        out["meta"]["current_focus_hobby"] = None
        if prev_phase != PHASE_ROUNDUP:
            out["meta"]["roundup_opening_done"] = False

    return out


def incomplete_hobby_names(state: dict[str, Any]) -> list[str]:
    names = discovery_hobby_names(state)
    hd = state.get("hobby_details") if isinstance(state.get("hobby_details"), dict) else {}
    out: list[str] = []
    for name in names:
        detail = hd.get(name)
        if not isinstance(detail, dict) or not hobby_fully_complete(detail):
            out.append(name)
    return out


def completed_hobby_names(state: dict[str, Any]) -> list[str]:
    names = discovery_hobby_names(state)
    incomplete = set(incomplete_hobby_names(state))
    return [n for n in names if n not in incomplete]


def resolve_focus_hobby_name(
    state: dict[str, Any],
    *,
    prefer_tracker_focus: bool = True,
) -> str | None:
    incomplete = incomplete_hobby_names(state)
    if not incomplete:
        return None

    if prefer_tracker_focus:
        meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
        focus = meta.get("current_focus_hobby")
        focus_str = focus.strip() if isinstance(focus, str) else None
        if focus_str and focus_str in incomplete:
            return focus_str

    names = discovery_hobby_names(state)
    completed_count = len(names) - len(incomplete)
    if completed_count > 0 and len(incomplete) <= completed_count:
        for name in reversed(names):
            if name in incomplete:
                return name
    return incomplete[0]


def first_incomplete_hobby_name(state: dict[str, Any]) -> str | None:
    return resolve_focus_hobby_name(state, prefer_tracker_focus=True)


def all_hobbies_completed(state: dict[str, Any]) -> bool:
    names = discovery_hobby_names(state)
    if not names:
        return False
    hd = state.get("hobby_details") if isinstance(state.get("hobby_details"), dict) else {}
    for name in names:
        detail = hd.get(name)
        if not isinstance(detail, dict) or not hobby_fully_complete(detail):
            return False
    return True


def deepdive_progress(state: dict[str, Any]) -> dict[str, Any]:
    names = discovery_hobby_names(state)
    hd = state.get("hobby_details") if isinstance(state.get("hobby_details"), dict) else {}
    completed: list[str] = []
    remaining: list[str] = []
    for name in names:
        detail = hd.get(name)
        if isinstance(detail, dict) and hobby_fully_complete(detail):
            completed.append(name)
        else:
            remaining.append(name)
    current = resolve_focus_hobby_name(state, prefer_tracker_focus=True)
    position = ""
    if current and current in names:
        position = f"{names.index(current) + 1} of {len(names)}"
    return {
        "all_hobbies": names,
        "completed_hobbies": completed,
        "remaining_hobbies": remaining,
        "current_hobby": current,
        "position": position,
    }


def roundup_recap_for_interviewer(state: dict[str, Any]) -> dict[str, Any]:
    """Structured recap for the roundup opening summary (discovery + deep dive)."""
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    hd = state.get("hobby_details") if isinstance(state.get("hobby_details"), dict) else {}
    hobbies: list[dict[str, Any]] = []
    for name in discovery_hobby_names(state):
        detail = hd.get(name) if isinstance(hd, dict) else None
        if not isinstance(detail, dict):
            detail = {}
        hobbies.append(
            {
                "name": name,
                "description": (detail.get("description") or "").strip(),
                "location": (detail.get("location") or "").strip(),
                "frequency": (detail.get("frequency") or "").strip(),
                "participants": (detail.get("participants") or "").strip(),
                "cost": (detail.get("cost") or "").strip(),
            }
        )
    return {
        "freetime_context": (discovery.get("freetime_context") or "").strip(),
        "hobbies": hobbies,
    }


def hobby_summary_for_interviewer(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        detail = {}
    missing = hobby_missing_fields(detail)
    return {
        "location": detail.get("location") or "",
        "frequency": detail.get("frequency") or "",
        "cost": detail.get("cost") or "",
        "description": detail.get("description") or "",
        "participants": detail.get("participants") or "",
        "missing_fields": missing,
        "required_fields": list(HOBBY_REQUIRED_FIELDS),
        "is_completed": bool(detail.get("is_completed")),
    }


def preserve_completed_hobbies(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    out = copy.deepcopy(after)
    before_hd = before.get("hobby_details")
    after_hd = out.get("hobby_details")
    if not isinstance(before_hd, dict) or not isinstance(after_hd, dict):
        return out

    for name, prev in before_hd.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(prev, dict) or not hobby_fully_complete(prev):
            continue
        new_detail = after_hd.get(name)
        if isinstance(new_detail, dict) and hobby_fully_complete(new_detail):
            continue
        after_hd[name] = copy.deepcopy(prev)

    out["hobby_details"] = after_hd
    return out


def enforce_focus_integrity(state: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(state)
    phase = meta_phase(out)

    if phase == PHASE_ROUNDUP:
        if all_hobbies_completed(out):
            out["meta"]["current_focus_hobby"] = None
            return out
        out["meta"]["phase"] = PHASE_DEEPDIVE

    if meta_phase(out) != PHASE_DEEPDIVE:
        return out

    names = discovery_hobby_names(out)
    incomplete = incomplete_hobby_names(out)

    if not incomplete:
        if names:
            out["meta"]["phase"] = PHASE_ROUNDUP
        out["meta"]["current_focus_hobby"] = None
        return out

    target = resolve_focus_hobby_name(out, prefer_tracker_focus=True)
    if target:
        out["meta"]["current_focus_hobby"] = target
    else:
        out["meta"]["current_focus_hobby"] = incomplete[0]

    return out


# Back-compat aliases used during migration
discovery_process_names = discovery_hobby_names
completed_process_names = completed_hobby_names
process_fully_complete = hobby_fully_complete
first_incomplete_process_name = first_incomplete_hobby_name
resolve_focus_process_name = resolve_focus_hobby_name
all_processes_completed = all_hobbies_completed
preserve_completed_processes = preserve_completed_hobbies
enforce_steps_on_state = enforce_hobbies_on_state
