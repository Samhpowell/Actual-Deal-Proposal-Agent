"""Strategic Model Routing Module for Enterprise Deal Qualification & Proposal Drafting.

Routes tasks dynamically between Gemini model tiers based on cognitive complexity,
latency targets, and token payload size:
- Fast Triage & Schema Validation -> `gemini-2.5-flash`
- Resource Sizing & Template Lookup -> `gemini-2.5-flash`
- Complex Deal Risk Analysis & Executive Proposal Authoring -> `gemini-2.5-pro`
"""

from typing import Any, Dict


class StrategicModelRouter:
    """Routes sub-agent tasks and user requests to the optimal Gemini model tier."""

    MODEL_TIERS: Dict[str, Dict[str, Any]] = {
        "FAST_TRIAGE": {
            "model_name": "gemini-2.5-flash",
            "temperature": 0.1,
            "max_output_tokens": 1024,
            "rationale": "Low-latency, cost-efficient tier for intent classification, qualification scoring, and resource math.",
        },
        "TEMPLATE_RETRIEVAL": {
            "model_name": "gemini-2.5-flash",
            "temperature": 0.0,
            "max_output_tokens": 1024,
            "rationale": "Deterministic tier for structured SOW template selection and schema validation.",
        },
        "COMPLEX_PROPOSAL_SYNTHESIS": {
            "model_name": "gemini-2.5-pro",
            "temperature": 0.3,
            "max_output_tokens": 4096,
            "rationale": "High-reasoning tier for multi-stakeholder risk synthesis and executive SOW proposal drafting.",
        },
    }

    @classmethod
    def route_task(cls, task_type: str, payload_size: int = 0) -> Dict[str, Any]:
        """Selects the optimal Gemini model configuration for a given task category."""
        normalized = (task_type or "").upper()
        if any(k in normalized for k in ["PROPOSAL", "DRAFT", "SYNTHES", "SOW", "EXECUTIVE"]):
            selected = dict(cls.MODEL_TIERS["COMPLEX_PROPOSAL_SYNTHESIS"])
        elif any(k in normalized for k in ["TEMPLATE", "RETRIEV", "LOOKUP"]):
            selected = dict(cls.MODEL_TIERS["TEMPLATE_RETRIEVAL"])
        elif payload_size > 4000:
            selected = dict(cls.MODEL_TIERS["COMPLEX_PROPOSAL_SYNTHESIS"])
        else:
            selected = dict(cls.MODEL_TIERS["FAST_TRIAGE"])

        selected["task_type"] = task_type
        return selected


global_model_router = StrategicModelRouter()
