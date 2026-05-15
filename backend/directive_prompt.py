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
    STEP_REQUIRED_FIELDS,
    deepdive_progress,
    discovery_process_names,
    first_active_step,
    first_incomplete_process_name,
    meta_phase,
    process_fully_complete,
    process_ready_for_exceptions,
    process_summary_for_interviewer,
    step_gap_comment,
    step_is_fully_mapped,
    step_mapping_progress,
    step_missing_fields,
)
from prompts import (
    DIRECTIVES_USER_FACING_RULES,
    DIRECTIVE_ACTIVE_STEP_TEMPLATE,
    DIRECTIVE_DEEPDIVE_ALL_PROCESSES_TEMPLATE,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL,
    DIRECTIVE_DISCOVERY_IN_PROGRESS,
    DIRECTIVE_DISCOVERY_JUST_CONFIRMED,
    DIRECTIVE_EXCEPTIONS_GATE_TEMPLATE,
    DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE,
    DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE,
    DIRECTIVE_PROCESS_STEPS_INCOMPLETE,
    DIRECTIVE_ROUNDUP,
    DIRECTIVE_SKIP_COMPLETED_PROCESSES_TEMPLATE,
    DIRECTIVE_SCOPE_CHECK_ONLY,
    DIRECTIVE_STEP_COMPLETE_TEMPLATE,
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


def _append_deepdive_process_directives(
    lines: list[str],
    *,
    active_name: str,
    proc: dict[str, Any],
    progress: dict[str, Any],
) -> None:
    completed_str = ", ".join(progress["completed_processes"]) or "(none yet)"
    remaining_str = ", ".join(progress["remaining_processes"]) or "(none)"
    progress_label = progress["position"] or (
        f"{len(progress['completed_processes'])}/{len(progress['all_processes'])}"
    )

    lines.append("")
    lines.append(_json_block("deepdive_progress", progress))
    lines.append("")
    if progress["completed_processes"]:
        lines.append("")
        lines.append(
            DIRECTIVE_SKIP_COMPLETED_PROCESSES_TEMPLATE.format(
                completed=completed_str,
                current=active_name,
            )
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

    internal = (proc.get("phase") or PROCESS_PHASE_STEPS).strip()

    if internal == PROCESS_PHASE_EXCEPTIONS:
        if not process_ready_for_exceptions(proc):
            lines.append("")
            lines.append(DIRECTIVE_PROCESS_STEPS_INCOMPLETE.format(process=active_name))
            internal = PROCESS_PHASE_STEPS
        else:
            lines.append("")
            lines.append(_json_block("active_process", {active_name: process_summary_for_interviewer(proc)}))
            lines.append("")
            lines.append(_json_block("exceptions", proc.get("exceptions") if isinstance(proc.get("exceptions"), list) else []))
            lines.append("")
            lines.append(DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE.format(focus=active_name))
            if not process_fully_complete(proc):
                next_proc = None
                for name in progress["all_processes"]:
                    if name != active_name and name in progress["remaining_processes"]:
                        next_proc = name
                        break
                lines.append("")
                lines.append(
                    DIRECTIVE_EXCEPTIONS_GATE_TEMPLATE.format(
                        process=active_name,
                        next_process=next_proc or "the next process",
                    )
                )
            return

    lines.append("")
    lines.append(_json_block("active_process", {active_name: process_summary_for_interviewer(proc)}))

    active_step, _ = first_active_step(proc)
    if active_step:
        step_prog = step_mapping_progress(proc)
        mapped_steps = ", ".join(step_prog["mapped_steps"]) or "(none yet)"
        step_progress_label = step_prog["position"] or (
            f"{len(step_prog['mapped_steps'])}/{len(step_prog['all_steps']) or 1}"
        )
        missing = step_missing_fields(active_step)
        missing_label = ", ".join(missing) if missing else "(none — all required fields filled)"
        lines.append("")
        lines.append(_json_block("step_progress", step_prog))
        lines.append("")
        lines.append(
            DIRECTIVE_ACTIVE_STEP_TEMPLATE.format(
                process=active_name,
                progress=step_progress_label,
                mapped=mapped_steps,
                missing=missing_label,
            )
        )
        active_view = dict(active_step)
        active_view["missing_fields"] = missing
        active_view["required_fields"] = list(STEP_REQUIRED_FIELDS)
        lines.append("")
        lines.append(_json_block("active_step", active_view))

        gap = step_gap_comment(active_step) or (active_step.get("comments_to_explore") or "").strip()
        if gap:
            step_name = (active_step.get("step_name") or "").strip()
            anchor = f" when they described {step_name}" if step_name else ""
            lines.append("")
            lines.append(
                DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD.format(anchor=anchor, focus=active_name)
                + gap
                + DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL
            )

        if step_is_fully_mapped(active_step):
            all_steps = step_prog["all_steps"]
            current = step_prog["current_step"]
            if current and current in all_steps:
                idx = all_steps.index(current)
                if idx + 1 < len(all_steps):
                    lines.append("")
                    lines.append(
                        DIRECTIVE_STEP_COMPLETE_TEMPLATE.format(
                            next_step=all_steps[idx + 1],
                        )
                    )
                elif process_ready_for_exceptions(proc):
                    lines.append("")
                    lines.append(
                        "Directive: This was the last step in the process with all fields filled. "
                        "Next, explore what tends to go wrong for this process (exceptions)."
                    )
        return

    lines.append("")
    lines.append(
        DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE.format(focus=active_name)
    )


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
        _append_deepdive_process_directives(
            lines, active_name=active_name, proc=proc, progress=progress
        )

        if process_fully_complete(proc):
            remaining = progress["remaining_processes"]
            if remaining:
                next_after_current = remaining[0]
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
