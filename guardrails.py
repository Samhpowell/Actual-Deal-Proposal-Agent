"""Input validation, commercial policy checks, and proposal completeness guardrails."""

import re
from typing import Any, Dict, List, Optional, Tuple


class SecurityAndPolicyGuardrails:
    """Enforces input security, commercial policy limits, and self-evaluation checks."""

    PROMPT_INJECTION_PATTERNS = [
        r"(?i)\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|system|above)\s+(?:instructions|rules|prompts|constraints)\b",
        r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:an?\s+)?(?:unrestricted|jailbroken|evil|rogue)\b",
        r"(?i)\b(?:reveal|print|dump|output)\s+(?:your\s+)?(?:system\s+prompt|secret\s+key|api_key|credentials)\b",
    ]

    REQUIRED_PROPOSAL_SECTIONS = [
        "Executive Summary",
        "Deal Qualification",
        "Scope of Work",
        "Target Deliverables",
        "Delivery Pod Staffing",
        "Key Assumptions",
    ]

    def __init__(self):
        self.compiled_injections = [re.compile(p) for p in self.PROMPT_INJECTION_PATTERNS]

    def validate_user_input(self, prompt_text: str) -> Tuple[bool, Optional[str]]:
        """Scans incoming user prompts for prompt injection or policy violations."""
        if not isinstance(prompt_text, str) or not prompt_text.strip():
            return False, "GUARDRAIL_BLOCK: Input prompt cannot be empty."

        for pattern in self.compiled_injections:
            if pattern.search(prompt_text):
                return (
                    False,
                    "SECURITY_GUARDRAIL_BLOCK: Potential prompt injection or instruction override attempt detected.",
                )
        return True, None

    def validate_commercial_policy(
        self, estimated_deal_value_usd: float, requested_discount_pct: float
    ) -> Tuple[bool, Optional[str]]:
        """Enforces enterprise commercial guardrails on deal value and discount ceiling."""
        if estimated_deal_value_usd <= 0:
            return (
                False,
                "COMMERCIAL_POLICY_BLOCK: Estimated deal value must be greater than $0.",
            )
        if requested_discount_pct < 0.0 or requested_discount_pct > 50.0:
            return (
                False,
                f"COMMERCIAL_POLICY_BLOCK: Requested discount ({requested_discount_pct}%) violates the 50.0% maximum commercial policy ceiling.",
            )
        return True, None

    def evaluate_proposal_quality(
        self, proposal_markdown: str, customer_name: str
    ) -> Dict[str, Any]:
        """Self-Evaluation Plugin (LLM-as-a-Judge / deterministic rubric check) for generated proposals."""
        missing_sections: List[str] = []
        for section in self.REQUIRED_PROPOSAL_SECTIONS:
            if section.lower() not in (proposal_markdown or "").lower():
                missing_sections.append(section)

        customer_grounded = (customer_name or "").lower() in (proposal_markdown or "").lower()
        passed = (len(missing_sections) == 0) and customer_grounded

        score = max(
            0,
            100 - (len(missing_sections) * 15) - (0 if customer_grounded else 25),
        )
        return {
            "self_eval_passed": passed,
            "quality_score": score,
            "customer_grounded": customer_grounded,
            "missing_sections": missing_sections,
            "evaluation_summary": (
                f"Self-evaluation PASSED ({score}/100): All 6 mandatory SOW sections verified and grounded for {customer_name}."
                if passed
                else f"Self-evaluation FAILED ({score}/100): Missing sections {missing_sections} or customer grounding."
            ),
        }


# ADK-compatible callback functions
def adk_before_model_guardrail_callback(
    callback_context: Any, llm_request: Any
) -> Optional[Any]:
    """ADK `before_model_callback` hook to inspect prompts before invoking Gemini."""
    text = str(getattr(llm_request, "contents", ""))
    passed, reason = global_guardrails.validate_user_input(text)
    if not passed:
        return {"status": "BLOCKED", "reason": reason}
    return None


def adk_before_tool_policy_callback(
    tool: Any, args: Dict[str, Any], tool_context: Any
) -> Optional[Dict[str, Any]]:
    """ADK `before_tool_callback` hook enforcing commercial policy limits before tool execution."""
    discount = float(args.get("requested_discount_pct", 0.0) or 0.0)
    deal_val = float(args.get("estimated_deal_value_usd", 100000.0) or 100000.0)
    passed, reason = global_guardrails.validate_commercial_policy(deal_val, discount)
    if not passed:
        return {
            "status": "ERROR",
            "error_code": "POLICY_GUARDRAIL_BLOCKED",
            "message": reason,
            "recovery_instruction": "Adjust `requested_discount_pct` to <= 50.0% and `estimated_deal_value_usd` > 0.",
        }
    return None


global_guardrails = SecurityAndPolicyGuardrails()
