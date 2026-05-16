"""Build phase-scoped state slices for the interviewer from Redis hobby JSON."""

from __future__ import annotations

import json
from typing import Any

from hobby_schema import (
    HOBBY_REQUIRED_FIELDS,
    PHASE_DEEPDIVE,
    PHASE_DISCOVERY,
    PHASE_ROUNDUP,
    completed_hobby_names,
    deepdive_progress,
    discovery_hobby_names,
    first_incomplete_hobby_name,
    hobby_fully_complete,
    hobby_gap_comment,
    hobby_missing_fields,
    hobby_summary_for_interviewer,
    meta_phase,
    resolve_focus_hobby_name,
    roundup_recap_for_interviewer,
)
from prompts import (
    DIRECTIVES_USER_FACING_RULES,
    DIRECTIVE_DEEPDIVE_ALL_HOBBIES_TEMPLATE,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD,
    DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL,
    DIRECTIVE_DEEPDIVE_OPEN_FIRST_HOBBY,
    DIRECTIVE_DEEPDIVE_OPEN_NEXT_HOBBY,
    DIRECTIVE_DISCOVERY_IN_PROGRESS,
    DIRECTIVE_HOBBY_FIELD_FOCUS_TEMPLATE,
    DIRECTIVE_HOBBY_NOT_STARTED_TEMPLATE,
    DIRECTIVE_ROUNDUP_FAVORITE,
    DIRECTIVE_ROUNDUP_OPENING,
    DIRECTIVE_SCOPE_CHECK_ONLY,
    DIRECTIVE_SKIP_COMPLETED_HOBBIES_TEMPLATE,
    DIRECTIVE_TRANSITION_TO_NEXT_HOBBY_TEMPLATE,
    DYNAMIC_WORKING_MEMORY_HEADER,
    format_directive_tangent,
)


def _json_block(label: str, payload: Any) -> str:
    return f"{label}:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


def _meta_for_interviewer(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": meta_phase({"meta": meta}),
        "current_focus_hobby": meta.get("current_focus_hobby"),
        "tangent_to_acknowledge": meta.get("tangent_to_acknowledge"),
        "favorite_hobby": meta.get("favorite_hobby") or "",
        "roundup_opening_done": bool(meta.get("roundup_opening_done")),
    }


def _append_deepdive_hobby_directives(
    lines: list[str],
    *,
    active_name: str,
    detail: dict[str, Any],
    progress: dict[str, Any],
) -> None:
    completed_str = ", ".join(progress["completed_hobbies"]) or "(none yet)"
    remaining_str = ", ".join(progress["remaining_hobbies"]) or "(none)"
    progress_label = progress["position"] or (
        f"{len(progress['completed_hobbies'])}/{len(progress['all_hobbies'])}"
    )

    lines.append("")
    lines.append(_json_block("deepdive_progress", progress))
    if progress["completed_hobbies"]:
        lines.append("")
        lines.append(
            DIRECTIVE_SKIP_COMPLETED_HOBBIES_TEMPLATE.format(
                completed=completed_str,
                current=active_name,
            )
        )
    lines.append("")
    lines.append(
        DIRECTIVE_DEEPDIVE_ALL_HOBBIES_TEMPLATE.format(
            progress=progress_label,
            completed=completed_str,
            remaining=remaining_str,
            current=active_name,
        )
    )
    lines.append("")
    lines.append(
        "Directive: For this hobby, capture every required field before moving on: "
        "description, location, frequency, participants, cost. "
        "Ask about ONE missing field per reply (see active_hobby.missing_fields)."
    )

    summary = hobby_summary_for_interviewer(detail)
    missing = hobby_missing_fields(detail)
    missing_label = ", ".join(missing) if missing else "(none — hobby complete in state)"
    filled = [f for f in HOBBY_REQUIRED_FIELDS if f not in missing]

    lines.append("")
    lines.append(_json_block("active_hobby", {active_name: summary}))

    if missing:
        lines.append("")
        lines.append(
            DIRECTIVE_HOBBY_FIELD_FOCUS_TEMPLATE.format(
                hobby=active_name,
                missing=missing_label,
                filled=", ".join(filled) or "(none yet)",
            )
        )
        gap = hobby_gap_comment(detail) or (detail.get("comments_to_explore") or "").strip()
        if gap:
            lines.append("")
            lines.append(
                DIRECTIVE_DEEPDIVE_MISSING_DETAIL_HEAD.format(focus=active_name)
                + gap
                + DIRECTIVE_DEEPDIVE_MISSING_DETAIL_TAIL
            )
    elif not hobby_fully_complete(detail):
        lines.append("")
        lines.append(
            f"Directive: All fields for '{active_name}' look filled — confirm briefly, "
            "then the state manager should mark is_completed true."
        )


def build_deepdive_entry_block(state: dict[str, Any]) -> str:
    """First deep-dive turn after discovery completes."""
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    names = discovery_hobby_names(state)
    focus = resolve_focus_hobby_name(state, prefer_tracker_focus=True) or (
        names[0] if names else "their first hobby"
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
                "freetime_context": discovery.get("freetime_context") or "",
                "identified_hobbies": names,
                "is_completed": True,
            },
        ),
        "",
        _json_block("deepdive_progress", deepdive_progress(state)),
        "",
        DIRECTIVE_DEEPDIVE_OPEN_FIRST_HOBBY.format(hobby=focus),
    ]
    return "\n".join(lines)


def build_dynamic_directive_block(state: dict[str, Any]) -> str:
    meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
    discovery = state.get("discovery") if isinstance(state.get("discovery"), dict) else {}
    hobby_details = (
        state.get("hobby_details") if isinstance(state.get("hobby_details"), dict) else {}
    )

    phase = meta_phase(state)
    meta_view = _meta_for_interviewer(meta)
    tangent = meta.get("tangent_to_acknowledge")
    tangent_str = tangent.strip() if isinstance(tangent, str) else None
    focus = meta.get("current_focus_hobby")
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
            "freetime_context": discovery.get("freetime_context") or "",
            "identified_hobbies": discovery_hobby_names(state),
            "is_completed": bool(discovery.get("is_completed")),
        }
        lines.append("")
        lines.append(_json_block("discovery", discovery_view))
        lines.append("")
        if discovery_view["is_completed"]:
            lines.append(
                "Directive: Hobby list is complete. The next user message should move to deepdive — "
                "if meta.phase is still discovery, wait one turn for the state update."
            )
        elif discovery_view["identified_hobbies"]:
            lines.append(DIRECTIVE_SCOPE_CHECK_ONLY)
        else:
            lines.append(DIRECTIVE_DISCOVERY_IN_PROGRESS)
        return "\n".join(lines)

    if phase == PHASE_DEEPDIVE:
        if not discovery.get("is_completed"):
            lines.append("")
            lines.append(
                "Directive: meta.phase is deepdive but discovery.is_completed is false — "
                "stay in discovery (sports & hobbies they do in freetime, confirm the full list) until "
                "discovery.is_completed is true."
            )
            lines.append("")
            lines.append(
                _json_block(
                    "discovery",
                    {
                        "freetime_context": discovery.get("freetime_context") or "",
                        "identified_hobbies": discovery_hobby_names(state),
                        "is_completed": False,
                    },
                )
            )
            return "\n".join(lines)

        active_name = first_incomplete_hobby_name(state)
        if not active_name:
            lines.append("")
            lines.append(
                "Directive: Every hobby in hobby_details is marked is_completed. "
                "Await roundup phase in the next state update."
            )
            return "\n".join(lines)

        detail = hobby_details.get(active_name)
        if not isinstance(detail, dict):
            detail = {}

        progress = deepdive_progress(state)
        missing = hobby_missing_fields(detail)
        if len(missing) == len(HOBBY_REQUIRED_FIELDS) and active_name == progress.get("current_hobby"):
            lines.append("")
            lines.append(DIRECTIVE_DEEPDIVE_OPEN_NEXT_HOBBY.format(hobby=active_name))
        elif len(missing) == len(HOBBY_REQUIRED_FIELDS):
            lines.append("")
            lines.append(DIRECTIVE_HOBBY_NOT_STARTED_TEMPLATE.format(hobby=active_name))

        _append_deepdive_hobby_directives(
            lines, active_name=active_name, detail=detail, progress=progress
        )

        if hobby_fully_complete(detail):
            remaining = [n for n in progress["remaining_hobbies"] if n != active_name]
            if remaining:
                lines.append("")
                lines.append(
                    DIRECTIVE_TRANSITION_TO_NEXT_HOBBY_TEMPLATE.format(
                        current=active_name,
                        next_hobby=remaining[0],
                    )
                )
        return "\n".join(lines)

    if phase == PHASE_ROUNDUP:
        all_names = discovery_hobby_names(state)
        completed = completed_hobby_names(state)
        favorite = (meta.get("favorite_hobby") or "").strip()
        opening_done = bool(meta.get("roundup_opening_done"))
        hobby_list = ", ".join(all_names) or "(none listed)"
        lines.append("")
        lines.append(_json_block("hobby_recap_for_summary", roundup_recap_for_interviewer(state)))
        lines.append("")
        lines.append(
            _json_block(
                "roundup_summary",
                {
                    "freetime_context": discovery.get("freetime_context") or "",
                    "all_hobbies": all_names,
                    "completed_hobbies": completed,
                    "favorite_hobby": favorite,
                    "roundup_opening_done": opening_done,
                },
            )
        )
        lines.append("")
        if not opening_done:
            lines.append(
                DIRECTIVE_ROUNDUP_OPENING.format(hobbies=hobby_list)
            )
        elif not favorite:
            lines.append(DIRECTIVE_ROUNDUP_FAVORITE.format(hobbies=hobby_list))
        else:
            lines.append(
                "Directive: Roundup is complete (summary given, completeness checked, favorite captured). "
                "You may give the final warm thank-you and tell them they can press the red button to end."
            )
        return "\n".join(lines)

    lines.append("")
    lines.append(f"Directive: Unknown meta.phase {phase!r}; follow discovery rules.")
    return "\n".join(lines)
