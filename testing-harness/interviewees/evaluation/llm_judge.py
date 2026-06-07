"""LLM-as-judge dimension scores (2b)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from interviewees.core.llm_json import MAX_JSON_ATTEMPTS, chat_json
from interviewees.evaluation.reconstructed_schema import GroundTruthProfile, ReconstructedPersona

JUDGE_DIMENSIONS = (
    "activity_coverage",
    "control_flow_and_handoff_fidelity",
    "attribute_accuracy",
    "exception_and_edge_case_capture",
    "faithfulness_no_hallucination",
)


class JudgeScores(BaseModel):
    activity_coverage: int = Field(ge=1, le=5)
    control_flow_and_handoff_fidelity: int = Field(ge=1, le=5)
    attribute_accuracy: int = Field(ge=1, le=5)
    exception_and_edge_case_capture: int = Field(ge=1, le=5)
    faithfulness_no_hallucination: int = Field(ge=1, le=5)


class JudgeOutput(BaseModel):
    scores: JudgeScores
    justifications: dict[str, str]


@dataclass
class JudgeReport:
    scores: dict[str, int]
    justifications: dict[str, str]
    raw_response: str


def run_llm_judge(
    truth: GroundTruthProfile,
    reconstructed: ReconstructedPersona,
    *,
    model: str,
) -> JudgeReport:
    system = (
        "You are an expert evaluator comparing a reconstructed process profile against "
        "ground truth from a process discovery interview. Score each dimension from 1 "
        "(bad/wrong) to 5 (perfect/identical). Ground truth excludes backstory. "
        "Return strict JSON only with keys: scores (object with the five dimension keys "
        "as integers 1-5) and justifications (object with the same keys, one sentence each)."
    )

    user_base = (
        "Compare RECONSTRUCTED (from interview only) vs GROUND TRUTH.\n\n"
        f"GROUND TRUTH:\n{json.dumps(truth.model_dump(mode='json'), indent=2, ensure_ascii=False)}\n\n"
        f"RECONSTRUCTED:\n{json.dumps(reconstructed.model_dump(mode='json'), indent=2, ensure_ascii=False)}\n\n"
        "Dimensions:\n"
        "1. activity_coverage — all original steps present; none missing or invented\n"
        "2. control_flow_and_handoff_fidelity — step sequence and handoff chain correct\n"
        "3. attribute_accuracy — tools, time_needed, handoff_to faithful\n"
        "4. exception_and_edge_case_capture — what_goes_wrong, impact, recovery correct\n"
        "5. faithfulness_no_hallucination — no asserted steps/tools/recovery absent from ground truth\n\n"
        'Output: {"scores": {...}, "justifications": {...}}'
    )

    last_error: str | None = None
    raw_response = ""
    for _attempt in range(MAX_JSON_ATTEMPTS):
        user_msg = user_base
        if last_error:
            user_msg += f"\n\nValidation error: {last_error}\nFix and return valid JSON."
        try:
            parsed, raw_response = chat_json(
                system=system,
                user=user_msg,
                model=model,
                temperature=0.2,
            )
            out = JudgeOutput.model_validate(parsed)
            return JudgeReport(
                scores=out.scores.model_dump(),
                justifications={k: v.strip() for k, v in out.justifications.items()},
                raw_response=raw_response,
            )
        except (json.JSONDecodeError, ValidationError, Exception) as e:
            last_error = str(e)

    raise RuntimeError(
        f"LLM judge failed after {MAX_JSON_ATTEMPTS} attempts. Last error: {last_error}"
    )
