"""LLM-as-judge dimension scores (2b)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger("harness.evaluation")

from pydantic import BaseModel, Field, ValidationError

from interviewees.core.llm_json import MAX_JSON_ATTEMPTS, chat_json
from interviewees.evaluation.defaults import DEFAULT_JUDGE_MODEL
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
    # Moved justifications FIRST to enforce Chain-of-Thought reasoning before scoring
    justifications: dict[str, str]
    scores: JudgeScores


@dataclass
class JudgeReport:
    scores: dict[str, int]
    justifications: dict[str, str]
    raw_response: str


def run_llm_judge(
    truth: GroundTruthProfile,
    reconstructed: ReconstructedPersona,
    *,
    model: str = DEFAULT_JUDGE_MODEL,
) -> JudgeReport:
    system = (
        "You are an expert AI evaluator assessing the performance of an automated interview system. "
        "Your task is to compare a RECONSTRUCTED process profile (extracted from an interview transcript) "
        "against the actual GROUND TRUTH profile.\n\n"
        "Evaluate the reconstruction based on semantic equivalence, not exact keyword matching. "
        "The Ground Truth may contain backstory elements; do not penalize the reconstructed profile for omitting backstory, "
        "focus only on the core process data.\n\n"
        "You must output strict JSON containing exactly two keys: 'justifications' (evaluate the dimension in 1-2 sentences) "
        "and 'scores' (integer 1-5). Generate justifications FIRST to inform your scores."
    )

    user_base = (
        "Please evaluate the RECONSTRUCTED profile against the GROUND TRUTH profile.\n\n"
        f"### GROUND TRUTH (Expected):\n{json.dumps(truth.model_dump(mode='json'), indent=2, ensure_ascii=False)}\n\n"
        f"### RECONSTRUCTED (Actual extraction):\n{json.dumps(reconstructed.model_dump(mode='json'), indent=2, ensure_ascii=False)}\n\n"
        "### SCORING RUBRIC (1-5):\n"
        "- 1: Complete failure / missing entirely / entirely hallucinated.\n"
        "- 2: Poor (Captures fragments, but major omissions or critical errors exist).\n"
        "- 3: Fair (Captures the core concept, but misses important details or has noticeable inaccuracies).\n"
        "- 4: Good (Mostly accurate and complete, only minor omissions or slight misinterpretations).\n"
        "- 5: Perfect (Semantically identical, completely accurate and comprehensive).\n\n"
        "### EVALUATION DIMENSIONS:\n"
        "1. activity_coverage (Recall) — Are all the original steps from the ground truth present? Penalize for missing steps.\n"
        "2. control_flow_and_handoff_fidelity — Is the logical sequence of steps and the chain of handoffs structurally correct?\n"
        "3. attribute_accuracy — For the steps identified, are the micro-details (tools used, time needed, specific handoff targets) faithful to the ground truth?\n"
        "4. exception_and_edge_case_capture — Did the interviewer successfully extract 'unhappy paths' (what goes wrong, impact, recovery)?\n"
        "5. faithfulness_no_hallucination (Precision) — Did the reconstructed profile invent steps, tools, or recoveries that were never in the ground truth? Penalize for hallucinations.\n\n"
        '### EXPECTED JSON FORMAT:\n'
        '{\n'
        '  "justifications": {\n'
        '    "activity_coverage": "<reasoning>",\n'
        '    "control_flow_and_handoff_fidelity": "<reasoning>",\n'
        '    "attribute_accuracy": "<reasoning>",\n'
        '    "exception_and_edge_case_capture": "<reasoning>",\n'
        '    "faithfulness_no_hallucination": "<reasoning>"\n'
        '  },\n'
        '  "scores": {\n'
        '    "activity_coverage": <int>,\n'
        '    "control_flow_and_handoff_fidelity": <int>,\n'
        '    "attribute_accuracy": <int>,\n'
        '    "exception_and_edge_case_capture": <int>,\n'
        '    "faithfulness_no_hallucination": <int>\n'
        '  }\n'
        '}'
    )

    last_error: str | None = None
    raw_response = ""
    for attempt in range(1, MAX_JSON_ATTEMPTS + 1):
        user_msg = user_base
        if last_error:
            user_msg += f"\n\nValidation error: {last_error}\nReview your formatting and return valid JSON adhering strictly to the schema."
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
            logger.warning("llm_judge attempt %s/%s failed: %s", attempt, MAX_JSON_ATTEMPTS, last_error)

    raise RuntimeError(
        f"LLM judge failed after {MAX_JSON_ATTEMPTS} attempts. Last error: {last_error}"
    )