"""Build phase-scoped state slices for the interviewer from Redis BPMN JSON."""

from __future__ import annotations

import json
from typing import Any

from bpmn_schema import (
    EXCEPTION_REQUIRED_FIELDS,
    PHASE_DEEPDIVE,
    PHASE_DISCOVERY,
    PHASE_ROUNDUP,
    PROCESS_PHASE_CONFIRM,
    PROCESS_PHASE_EXCEPTIONS,
    PROCESS_PHASE_STEPS,
    STEP_REQUIRED_FIELDS,
    completed_process_names,
    deepdive_progress,
    discovery_process_names,
    exception_gap_comment,
    exception_is_fully_mapped,
    exception_mapping_progress,
    exception_missing_fields,
    first_active_exception,
    first_active_step,
    first_incomplete_process_name,
    meta_phase,
    resolve_focus_process_name,
    process_fully_complete,
    process_ready_for_confirm,
    process_ready_for_exceptions,
    process_summary_for_interviewer,
    step_gap_comment,
    step_is_fully_mapped,
    step_mapping_progress,
    step_missing_fields,
)
from prompts import (
    DIRECTIVES_USER_FACING_RULES,
    DIRECTIVE_ACTIVE_EXCEPTION_TEMPLATE,
    DIRECTIVE_ACTIVE_STEP_TEMPLATE,
    DIRECTIVE_DEEPDIVE_ALL_PROCESSES_TEMPLATE,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL,
    DIRECTIVE_DEEPDIVE_OPEN_FIRST_PROCESS,
    DIRECTIVE_DEEPDIVE_OPEN_NEXT_PROCESS,
    DIRECTIVE_DISCOVERY_IN_PROGRESS,
    DIRECTIVE_EXCEPTION_COMPLETE_TEMPLATE,
    DIRECTIVE_FINAL_ROUNDUP,
    DIRECTIVE_EXCEPTIONS_GATE_TEMPLATE,
    DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE,
    DIRECTIVE_LAST_STEP_ACTIVE_TEMPLATE,
    DIRECTIVE_LAST_STEP_READY_FOR_EXCEPTIONS,
    DIRECTIVE_PROCESS_CONFIRM_GATE_TEMPLATE,
    DIRECTIVE_PROCESS_CONFIRM_TEMPLATE,
    DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE,
    DIRECTIVE_PROCESS_STEPS_INCOMPLETE,
    DIRECTIVE_SKIP_COMPLETED_PROCESSES_TEMPLATE,
    DIRECTIVE_SCOPE_CHECK_ONLY,
    DIRECTIVE_START_EXCEPTIONS_SUBPHASE,
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
    lines.append("")
    lines.append(
        "Directive: For this process, deep dive has two sub-phases in order: "
        "(1) each step in active_step — tools, time, handoffs; "
        "(2) each exception in active_exception — what goes wrong, impact, recovery. "
        "Finish sub-phase 1 completely before sub-phase 2."
    )

    internal = (proc.get("phase") or PROCESS_PHASE_STEPS).strip()

    if internal == PROCESS_PHASE_CONFIRM:
        if not process_ready_for_confirm(proc):
            internal = (
                PROCESS_PHASE_EXCEPTIONS
                if process_ready_for_exceptions(proc)
                else PROCESS_PHASE_STEPS
            )
        else:
            lines.append("")
            lines.append(_json_block("active_process", {active_name: process_summary_for_interviewer(proc)}))
            next_proc = None
            for name in progress["all_processes"]:
                if name != active_name and name in progress["remaining_processes"]:
                    next_proc = name
                    break
            lines.append("")
            if proc.get("summary_confirmed"):
                lines.append(
                    DIRECTIVE_TRANSITION_TO_NEXT_PROCESS_TEMPLATE.format(
                        current=active_name,
                        next_process=next_proc or "the next process",
                    )
                )
            else:
                lines.append(
                    DIRECTIVE_PROCESS_CONFIRM_TEMPLATE.format(
                        process=active_name,
                        next_process=next_proc or "the next process",
                    )
                )
                lines.append("")
                lines.append(
                    DIRECTIVE_PROCESS_CONFIRM_GATE_TEMPLATE.format(
                        process=active_name,
                        next_process=next_proc or "the next process",
                    )
                )
            return

    if internal == PROCESS_PHASE_EXCEPTIONS:
        if not process_ready_for_exceptions(proc):
            lines.append("")
            lines.append(DIRECTIVE_PROCESS_STEPS_INCOMPLETE.format(process=active_name))
            internal = PROCESS_PHASE_STEPS
        else:
            lines.append("")
            lines.append(_json_block("active_process", {active_name: process_summary_for_interviewer(proc)}))
            lines.append("")
            lines.append(DIRECTIVE_START_EXCEPTIONS_SUBPHASE.format(process=active_name))
            active_exc, _ = first_active_exception(proc)
            if active_exc:
                exc_prog = exception_mapping_progress(proc)
                mapped_exc = ", ".join(exc_prog["mapped_exceptions"]) or "(none yet)"
                exc_progress_label = exc_prog["position"] or (
                    f"{len(exc_prog['mapped_exceptions'])}/{len(exc_prog['all_exceptions']) or 1}"
                )
                missing_exc = exception_missing_fields(active_exc)
                missing_exc_label = ", ".join(missing_exc) if missing_exc else "(none)"
                lines.append("")
                lines.append(_json_block("exception_progress", exc_prog))
                lines.append("")
                lines.append(
                    DIRECTIVE_ACTIVE_EXCEPTION_TEMPLATE.format(
                        process=active_name,
                        progress=exc_progress_label,
                        mapped=mapped_exc,
                        missing=missing_exc_label,
                    )
                )
                exc_view = dict(active_exc)
                exc_view["missing_fields"] = missing_exc
                exc_view["required_fields"] = list(EXCEPTION_REQUIRED_FIELDS)
                lines.append("")
                lines.append(_json_block("active_exception", exc_view))
                gap_exc = exception_gap_comment(active_exc) or (
                    active_exc.get("comments_to_explore") or ""
                ).strip()
                if gap_exc:
                    lines.append("")
                    lines.append(
                        DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD.format(
                            anchor="", focus=active_name
                        )
                        + gap_exc
                        + DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL
                    )
                if exception_is_fully_mapped(active_exc):
                    all_exc = exc_prog["all_exceptions"]
                    current_exc_label = exc_prog["current_exception"]
                    if current_exc_label and current_exc_label in all_exc:
                        idx = all_exc.index(current_exc_label)
                        if idx + 1 < len(all_exc):
                            lines.append("")
                            lines.append(
                                DIRECTIVE_EXCEPTION_COMPLETE_TEMPLATE.format(
                                    next_exc=all_exc[idx + 1],
                                )
                            )
                        elif process_ready_for_confirm(proc):
                            lines.append("")
                            lines.append(
                                "Directive: All exception scenarios for this process are complete in state. "
                                "Next turn: summarize the process and ask if you got anything wrong."
                            )
            else:
                lines.append("")
                lines.append(DIRECTIVE_EXCEPTIONS_PHASE_TEMPLATE.format(focus=active_name))
            if not process_fully_complete(proc) and not process_ready_for_confirm(proc):
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
        all_steps = step_prog["all_steps"]
        current = step_prog["current_step"]
        is_last_step = bool(
            current and current in all_steps and all_steps.index(current) == len(all_steps) - 1
        )
        if is_last_step and not step_is_fully_mapped(active_step):
            step_label = (active_step.get("step_name") or "").strip() or current or "this step"
            lines.append("")
            lines.append(
                DIRECTIVE_LAST_STEP_ACTIVE_TEMPLATE.format(
                    process=active_name,
                    step=step_label,
                    missing=missing_label,
                )
            )
        else:
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
                        DIRECTIVE_LAST_STEP_READY_FOR_EXCEPTIONS.format(process=active_name)
                    )
        return

    lines.append("")
    lines.append(
        DIRECTIVE_PROCESS_NOT_IN_DETAILS_TEMPLATE.format(focus=active_name)
    )


def build_deepdive_entry_block(state: dict[str, Any]) -> str:
    """First deep-dive turn after discovery completes — open with a question on the focus process."""
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    names = discovery_process_names(state)
    focus = resolve_focus_process_name(state, prefer_tracker_focus=True) or (
        names[0] if names else "their first main task"
    )
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
                "identified_main_processes": names,
                "is_completed": True,
            },
        ),
        "",
        _json_block("deepdive_progress", deepdive_progress(state)),
        "",
        DIRECTIVE_DEEPDIVE_OPEN_FIRST_PROCESS.format(process=focus),
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
                "Directive: Discovery list is complete. The next user message should move to deepdive — "
                "if meta.phase is still discovery, wait one turn for the state update."
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
        steps = proc.get("steps") if isinstance(proc.get("steps"), list) else []
        if not steps and active_name == progress.get("current_process"):
            lines.append("")
            lines.append(
                DIRECTIVE_DEEPDIVE_OPEN_NEXT_PROCESS.format(process=active_name)
            )

        _append_deepdive_process_directives(
            lines, active_name=active_name, proc=proc, progress=progress
        )

        if process_fully_complete(proc):
            remaining = [n for n in progress["remaining_processes"] if n != active_name]
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
        all_names = discovery_process_names(state)
        completed = completed_process_names(state)
        lines.append("")
        lines.append(
            _json_block(
                "roundup_summary",
                {
                    "interviewee_role": discovery.get("interviewee_role") or "",
                    "all_processes": all_names,
                    "completed_processes": completed,
                },
            )
        )
        lines.append("")
        lines.append(
            DIRECTIVE_FINAL_ROUNDUP.format(
                processes=", ".join(all_names) or "(none listed)",
            )
        )
        return "\n".join(lines)

    lines.append("")
    lines.append(f"Directive: Unknown meta.phase {phase!r}; follow discovery rules.")
    return "\n".join(lines)
