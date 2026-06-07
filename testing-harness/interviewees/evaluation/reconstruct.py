"""LLM reconstruction from interview artifacts only (no ground-truth access)."""

from __future__ import annotations

import json

from pydantic import ValidationError

from interviewees.core.llm_json import MAX_JSON_ATTEMPTS, chat_json
from interviewees.evaluation.interview_artifacts import (
    InterviewArtifacts,
    format_artifacts_for_prompt,
)
from interviewees.evaluation.reconstructed_schema import ReconstructedPersona

_RECONSTRUCTION_SCHEMA_HINT = """
Output a single JSON object with these exact top-level keys:
{
  "name": string (only if stated in interview; else ""),
  "role": string (only if stated or clearly implied; else ""),
  "processes": [
    {
      "process_name": string (only if identified; else ""),
      "steps": [
        {
          "step_name": string,
          "software_tools_used": string[] (only tools actually mentioned; else []),
          "time_needed": string (only if stated; else ""),
          "handoff_to": string or null (only if stated; else null)
        }
      ],
      "exceptions": [
        {
          "what_goes_wrong": string,
          "impact": string,
          "recovery": string
        }
      ]
    }
  ]
}

Use empty string "", empty array [], or null as appropriate when information was NOT
discussed. Do NOT invent steps, tools, times, handoffs, or exceptions.
"""


def reconstruct_interview(
    artifacts: InterviewArtifacts,
    *,
    model: str,
) -> ReconstructedPersona:
    system = (
        "You extract structured process knowledge from interview outputs for evaluation. "
        "You must use ONLY information explicitly present in the provided transcript, "
        "summary, and state JSON. This is strict extraction, not persona creation: "
        "do not infer, guess, or complete missing fields. If something was not discussed, "
        "leave it empty (\"\"), use [], or use null for handoff_to. Write in English. "
        "Return valid JSON only."
    )

    user_base = (
        f"{format_artifacts_for_prompt(artifacts)}\n\n"
        f"{_RECONSTRUCTION_SCHEMA_HINT}"
    )

    last_error: str | None = None
    for attempt in range(1, MAX_JSON_ATTEMPTS + 1):
        user_msg = user_base
        if last_error:
            user_msg += (
                f"\n\nPrevious attempt failed validation:\n{last_error}\n\n"
                "Fix and return only valid JSON."
            )
        try:
            parsed, _raw = chat_json(
                system=system,
                user=user_msg,
                model=model,
                temperature=0.3,
            )
            return ReconstructedPersona.model_validate(parsed)
        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON: {e}"
        except ValidationError as e:
            last_error = str(e)
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(
        f"Reconstruction failed for {artifacts.system} in {artifacts.folder.name} "
        f"after {MAX_JSON_ATTEMPTS} attempts. Last error: {last_error}"
    )
