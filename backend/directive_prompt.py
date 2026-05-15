"""Build phase-scoped state slices for the interviewer from Redis BPMN JSON."""

from __future__ import annotations

import json
from typing import Any

from bpmn_schema import (
    PHASE_DEEPDIVE,
    PHASE_DISCOVERY,
    PHASE_ROUNDUP,
    PROCESS_PHASE_EXCEPTIONS,
    PROCESS_PHASE_STEPS,
    deepdive_progress,
    discovery_process_names,
    first_incomplete_process_name,
    meta_phase,
)
from prompts import (
    DIRECTIVES_USER_FACING_RULES,
    DIRECTIVE_DEEPDIVE_ALL_PROCESSES_TEMPLATE,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL,
    DIRECTIVE_DISCOVERY_IN_PROGRESS,
    DIRECTIVE_DISCOVERY_JUST_CONFIRMED,
    DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE,
    DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE,
    DIRECTIVE_ROUNDUP,
    DIRECTIVE_SCOPE_CHECK_ONLY,
    DIRECTIVE_TRANSITION_TO_NEXT_PROCESS_TEMPLATE,
    DYNAMIC_WORKING_MEMORY_HEADER,
    format_directive_tangent,
)


def _json_block(label: str, payload: Any) -> str:
    return f"{label}:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


def _meta_for_interviewer(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": meta_phase({"meta": meta}),
        "current_focus_process": meta.get("current_focus_process"),
        "tangent_to_acknowledge": meta.get("tangent_to_acknowledge"),
    }


def _first_step_needing_detail(
    proc: dict[str, Any],
) -> tuple[str | None, str | None]:
    steps = proc.get("steps")
    if not isinstance(steps, list):
        return None, None
    for s in steps:
        if not isinstance(s, dict):
            continue
        name = (s.get("step_name") or "").strip()
        cte = (s.get("comments_to_explore") or "").strip()
        if cte:
            return name or None, cte
    return None, None


def _directive_for_active_process(name: str, proc: dict[str, Any]) -> str:
    if proc.get("is_completed"):
        return (
            f"Directive: Process '{name}' is marked complete internally — do not deep-dive it again "
            "unless the interviewee corrects something."
        )

    internal = (proc.get("phase") or PROCESS_PHASE_STEPS).strip()
    step_name, comments = _first_step_needing_detail(proc)

    if internal == PROCESS_PHASE_STEPS and comments:
        anchor = f" when they described {step_name}" if step_name else ""
        return (
            DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD.format(anchor=anchor, focus=name)
            + comments
            + DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL
        )

    if internal == PROCESS_PHASE_EXCEPTIONS:
        return DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE.format(focus=name)

    return DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE.format(focus=name)


def build_discovery_just_confirmed_block(state: dict[str, Any]) -> str:
    """One-turn bridge after discovery.is_completed flips — acknowledge only, no deep dive yet."""
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    lines: list[str] = [
        DYNAMIC_WORKING_MEMORY_HEADER,
        DIRECTIVES_USER_FACING_RULES,
        "",
        _json_block("meta", _meta_for_interviewer(meta)),
        "",
        _json_block(
            "discovery",
            {
                "interviewee_role": discovery.get("interviewee_role") or "",
                "identified_main_processes": discovery_process_names(state),
                "is_completed": True,
            },
        ),
        "",
        DIRECTIVE_DISCOVERY_JUST_CONFIRMED,
    ]
    return "\n".join(lines)


def build_dynamic_directive_block(state: dict[str, Any]) -> str:
    """
    Expose only the slice of Redis state the interviewer needs for the current meta.phase.
    Always includes meta; discovery / one process / roundup rules apply per phase.
    """
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    process_details = (
        state.get("process_details")
        if isinstance(state.get("process_details"), dict)
        else {}
    )

    phase = meta_phase(state)
    meta_view = _meta_for_interviewer(meta)
    tangent = meta.get("tangent_to_acknowledge")
    tangent_str = tangent.strip() if isinstance(tangent, str) else None
    focus = meta.get("current_focus_process")
    focus_str = focus.strip() if isinstance(focus, str) else None

    lines: list[str] = [
        DYNAMIC_WORKING_MEMORY_HEADER,
        DIRECTIVES_USER_FACING_RULES,
        "",
        _json_block("meta", meta_view),
    ]

    if tangent_str:
        lines.append("")
        lines.append(format_directive_tangent(tangent_str, focus_str))
        return "\n".join(lines)

    if phase == PHASE_DISCOVERY:
        discovery_view = {
            "interviewee_role": discovery.get("interviewee_role") or "",
            "identified_main_processes": discovery_process_names(state),
            "is_completed": bool(discovery.get("is_completed")),
        }
        lines.append("")
        lines.append(_json_block("discovery", discovery_view))
        lines.append("")
        if discovery_view["is_completed"]:
            lines.append(
                "Directive: Discovery is complete. Wait for the next state update — "
                "do not start step-by-step deep dive until meta.phase is deepdive."
            )
        elif discovery_view["identified_main_processes"]:
            lines.append(DIRECTIVE_SCOPE_CHECK_ONLY)
        else:
            lines.append(DIRECTIVE_DISCOVERY_IN_PROGRESS)
        return "\n".join(lines)

    if phase == PHASE_DEEPDIVE:
        if not discovery.get("is_completed"):
            lines.append("")
            lines.append(
                "Directive: meta.phase is deepdive but discovery.is_completed is false — "
                "stay in discovery mode (role, main tasks, confirm the full list) until "
                "discovery.is_completed is true."
            )
            lines.append("")
            lines.append(
                _json_block(
                    "discovery",
                    {
                        "interviewee_role": discovery.get("interviewee_role") or "",
                        "identified_main_processes": discovery_process_names(state),
                        "is_completed": False,
                    },
                )
            )
            return "\n".join(lines)

        active_name = first_incomplete_process_name(state)
        if not active_name:
            lines.append("")
            lines.append(
                "Directive: Every process in process_details is marked is_completed. "
                "Await roundup phase in the next state update."
            )
            return "\n".join(lines)

        proc = process_details.get(active_name)
        if not isinstance(proc, dict):
            proc = {}

        progress = deepdive_progress(state)
        completed_str = ", ".join(progress["completed_processes"]) or "(none yet)"
        remaining_str = ", ".join(progress["remaining_processes"]) or "(none)"
        progress_label = progress["position"] or f"{len(progress['completed_processes'])}/{len(progress['all_processes'])}"

        lines.append("")
        lines.append(_json_block("deepdive_progress", progress))
        lines.append("")
        if progress["completed_processes"]:
            lines.append("")
            lines.append(
                "Directive: These processes are already fully explored — do NOT ask about them again: "
                f"{completed_str}."
            )
        lines.append("")
        lines.append(
            DIRECTIVE_DEEPDIVE_ALL_PROCESSES_TEMPLATE.format(
                progress=progress_label,
                completed=completed_str,
                remaining=remaining_str,
                current=active_name,
            )
        )
        lines.append("")
        lines.append(_json_block("active_process", {active_name: proc}))
        lines.append("")
        lines.append(_directive_for_active_process(active_name, proc))

        remaining = progress["remaining_processes"]
        if len(remaining) > 1 or (len(remaining) == 1 and remaining[0] != active_name):
            next_after_current = None
            found_current = False
            for name in progress["all_processes"]:
                if name == active_name:
                    found_current = True
                    continue
                if found_current and name in remaining:
                    next_after_current = name
                    break
            if next_after_current:
                lines.append("")
                lines.append(
                    DIRECTIVE_TRANSITION_TO_NEXT_PROCESS_TEMPLATE.format(
                        current=active_name,
                        next_process=next_after_current,
                    )
                )
        return "\n".join(lines)

    if phase == PHASE_ROUNDUP:
        lines.append("")
        lines.append(
            _json_block(
                "discovery_summary",
                {
                    "interviewee_role": discovery.get("interviewee_role") or "",
                    "identified_main_processes": discovery_process_names(state),
                },
            )
        )
        lines.append("")
        lines.append(DIRECTIVE_ROUNDUP)
        return "\n".join(lines)

    lines.append("")
    lines.append(f"Directive: Unknown meta.phase {phase!r}; follow discovery rules.")
    return "\n".join(lines)
