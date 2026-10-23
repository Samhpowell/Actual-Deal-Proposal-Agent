"""Tools and Schemas for Enterprise Deal Qualification and SOW Proposal Drafting."""

from typing import Any, Dict, List, Optional, Tuple

try:
    from pydantic import BaseModel, Field
except ImportError:

    def Field(default: Any = None, **kwargs: Any) -> Any:  # type: ignore
        return default

    class BaseModel:  # type: ignore
        """Fallback schema base class when pydantic is not installed in system Python."""

        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            return dict(self.__dict__)

from .memory_store import DEFAULT_PROPOSAL_TEMPLATES, global_memory_store


# =============================================================================
# 1. Explicit Pydantic Input & Output Schemas
# =============================================================================
class DealQualificationInputSchema(BaseModel):
    """Strict input validation schema for enterprise deal qualification."""

    customer_name: str = Field(..., min_length=2, description="Enterprise customer organization name.")
    opportunity_name: str = Field(..., min_length=3, description="Title of the AI or cloud consulting opportunity.")
    estimated_deal_value_usd: float = Field(
        ..., gt=0, le=50000000, description="Estimated Total Contract Value (TCV) in USD."
    )
    executive_sponsor_identified: bool = Field(
        ..., description="True if a VP/C-level Economic Buyer or budget owner is confirmed."
    )
    budget_confirmed: bool = Field(
        ..., description="True if customer funding or committed budget is verified."
    )
    quantified_business_metrics: str = Field(
        ..., description="Summary of target business KPIs or ROI metrics."
    )
    technical_readiness_level: str = Field(
        default="MEDIUM",
        description="Customer cloud & data readiness level: 'LOW', 'MEDIUM', or 'HIGH'.",
    )
    target_timeline_weeks: int = Field(
        default=8, ge=1, le=52, description="Customer requested delivery timeline in weeks."
    )


class DealQualificationOutputSchema(BaseModel):
    """Strict output schema for deal qualification results."""

    status: str
    customer_name: str
    opportunity_name: str
    qualification_score: int
    max_score: int = 100
    qualification_status: str
    recommended_tier: str
    dimension_breakdown: Dict[str, int]
    identified_risks_and_gaps: List[str]
    next_step_guidance: str


class ResourceEstimateInputSchema(BaseModel):
    """Strict input validation schema for delivery pod resource and pricing estimation."""

    recommended_tier: str = Field(
        ...,
        description="Engagement tier key: 'tier_1_discovery_sprint', 'tier_2_pilot_mvp', or 'tier_3_enterprise_scale'.",
    )
    custom_duration_weeks: Optional[int] = Field(
        default=None, ge=2, le=52, description="Optional override for sprint duration in weeks."
    )
    requested_discount_pct: float = Field(
        default=0.0, ge=0.0, le=50.0, description="Requested commercial discount percentage (0 to 50)."
    )


class ProposalDraftInputSchema(BaseModel):
    """Strict input validation schema for generating a structured Statement of Work proposal."""

    customer_name: str = Field(..., min_length=2, description="Enterprise customer name.")
    opportunity_name: str = Field(..., min_length=3, description="Opportunity title.")
    business_problem_summary: str = Field(
        ..., min_length=10, description="Description of the client's business challenge and target outcomes."
    )
    qualification_result: Dict[str, Any] = Field(
        ..., description="Output dictionary from `evaluate_deal_qualification_criteria`."
    )
    resource_estimate: Dict[str, Any] = Field(
        ..., description="Output dictionary from `calculate_delivery_resource_estimate`."
    )
    template_payload: Dict[str, Any] = Field(
        ..., description="Output dictionary from `retrieve_proposal_template_by_tier`."
    )


# =============================================================================
# 2. Explicit JSON Schemas Dictionary for LLM Function Calling Validation
# =============================================================================
TOOL_JSON_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "evaluate_deal_qualification_criteria": {
        "type": "object",
        "properties": {
            "customer_name": {"type": "string", "minLength": 2},
            "opportunity_name": {"type": "string", "minLength": 3},
            "estimated_deal_value_usd": {"type": "number", "minimum": 1, "maximum": 50000000},
            "executive_sponsor_identified": {"type": "boolean"},
            "budget_confirmed": {"type": "boolean"},
            "quantified_business_metrics": {"type": "string"},
            "technical_readiness_level": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH"],
            },
            "target_timeline_weeks": {"type": "integer", "minimum": 1, "maximum": 52},
        },
        "required": [
            "customer_name",
            "opportunity_name",
            "estimated_deal_value_usd",
            "executive_sponsor_identified",
            "budget_confirmed",
            "quantified_business_metrics",
        ],
    },
    "calculate_delivery_resource_estimate": {
        "type": "object",
        "properties": {
            "recommended_tier": {
                "type": "string",
                "enum": [
                    "tier_1_discovery_sprint",
                    "tier_2_pilot_mvp",
                    "tier_3_enterprise_scale",
                ],
            },
            "custom_duration_weeks": {"type": "integer", "minimum": 2, "maximum": 52},
            "requested_discount_pct": {"type": "number", "minimum": 0.0, "maximum": 50.0},
        },
        "required": ["recommended_tier"],
    },
    "retrieve_proposal_template_by_tier": {
        "type": "object",
        "properties": {
            "tier_key": {
                "type": "string",
                "enum": [
                    "tier_1_discovery_sprint",
                    "tier_2_pilot_mvp",
                    "tier_3_enterprise_scale",
                ],
            }
        },
        "required": ["tier_key"],
    },
    "generate_structured_proposal_draft": {
        "type": "object",
        "properties": {
            "customer_name": {"type": "string", "minLength": 2},
            "opportunity_name": {"type": "string", "minLength": 3},
            "business_problem_summary": {"type": "string", "minLength": 10},
            "qualification_result": {"type": "object"},
            "resource_estimate": {"type": "object"},
            "template_payload": {"type": "object"},
        },
        "required": [
            "customer_name",
            "opportunity_name",
            "business_problem_summary",
            "qualification_result",
            "resource_estimate",
            "template_payload",
        ],
    },
}


def validate_tool_arguments(
    tool_name: str, args: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Validates tool arguments against explicit JSON schemas before execution."""
    schema = TOOL_JSON_SCHEMAS.get(tool_name)
    if not schema:
        return True, None

    for req_key in schema.get("required", []):
        if req_key not in args or args[req_key] is None:
            return (
                False,
                f"Missing required parameter '{req_key}' for tool '{tool_name}'.",
            )

    props = schema.get("properties", {})
    for key, val in args.items():
        if val is None or key not in props:
            continue
        spec = props[key]
        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(val, str):
            return False, f"Parameter '{key}' must be a string, got {type(val).__name__}."
        if expected_type == "boolean" and not isinstance(val, bool):
            return False, f"Parameter '{key}' must be a boolean, got {type(val).__name__}."
        if expected_type == "integer" and (not isinstance(val, int) or isinstance(val, bool)):
            return False, f"Parameter '{key}' must be an integer, got {type(val).__name__}."
        if expected_type == "number" and (
            not isinstance(val, (int, float)) or isinstance(val, bool)
        ):
            return False, f"Parameter '{key}' must be a number, got {type(val).__name__}."
        if expected_type == "object" and not isinstance(val, dict):
            return False, f"Parameter '{key}' must be a dict/object, got {type(val).__name__}."

        if "minLength" in spec and isinstance(val, str) and len(val.strip()) < spec["minLength"]:
            return (
                False,
                f"Parameter '{key}' length ({len(val.strip())}) is shorter than minimum {spec['minLength']}.",
            )
        if "minimum" in spec and isinstance(val, (int, float)) and val < spec["minimum"]:
            return False, f"Parameter '{key}' value {val} is below minimum {spec['minimum']}."
        if "maximum" in spec and isinstance(val, (int, float)) and val > spec["maximum"]:
            return False, f"Parameter '{key}' value {val} exceeds maximum {spec['maximum']}."
        if "enum" in spec and val not in spec["enum"]:
            return (
                False,
                f"Parameter '{key}' value '{val}' must be one of {spec['enum']}.",
            )

    return True, None


# =============================================================================
# 3. Domain Tools with Comprehensive Docstrings & Guided Error Recovery
# =============================================================================
def evaluate_deal_qualification_criteria(
    customer_name: str,
    opportunity_name: str,
    estimated_deal_value_usd: float,
    executive_sponsor_identified: bool,
    budget_confirmed: bool,
    quantified_business_metrics: str,
    technical_readiness_level: str = "MEDIUM",
    target_timeline_weeks: int = 8,
) -> Dict[str, Any]:
    """Evaluates an enterprise opportunity against weighted MEDDPICC/BANT qualification criteria.

    Scores the deal across five dimensions (0-20 points each, 100 points total):
    Business Metrics, Executive Sponsor, Technical Readiness, Confirmed Budget, and Timeline.
    Determines whether the deal is qualified for proposal drafting and selects the optimal
    Statement of Work (SOW) engagement tier.

    Args:
        customer_name: Name of the enterprise customer organization (min 2 chars).
        opportunity_name: Descriptive title of the consulting or AI opportunity.
        estimated_deal_value_usd: Estimated Total Contract Value (TCV) in US dollars (> 0).
        executive_sponsor_identified: True if an executive budget holder (VP/C-Suite) is engaged.
        budget_confirmed: True if customer funding or budget allocation is confirmed.
        quantified_business_metrics: Specific KPIs, cost savings, or revenue targets.
        technical_readiness_level: Cloud and data readiness level ('LOW', 'MEDIUM', or 'HIGH').
        target_timeline_weeks: Customer target delivery duration in weeks (1 to 52).

    Returns:
        Dict[str, Any]: Structured qualification scorecard containing:
            - status (str): 'SUCCESS' or 'ERROR'.
            - qualification_score (int): Total weighted score from 0 to 100.
            - qualification_status (str): 'QUALIFIED_READY_FOR_PROPOSAL',
              'NEEDS_DISCOVERY_REFINEMENT', or 'DISQUALIFIED_HIGH_RISK'.
            - recommended_tier (str): 'tier_1_discovery_sprint', 'tier_2_pilot_mvp',
              or 'tier_3_enterprise_scale'.
            - dimension_breakdown (Dict[str, int]): Score per qualification pillar.
            - identified_risks_and_gaps (List[str]): Actionable list of deal risks.
            - recovery_instruction (str, optional): Self-correction guidance if an error occurs.
    """
    raw_args = {
        "customer_name": customer_name,
        "opportunity_name": opportunity_name,
        "estimated_deal_value_usd": estimated_deal_value_usd,
        "executive_sponsor_identified": executive_sponsor_identified,
        "budget_confirmed": budget_confirmed,
        "quantified_business_metrics": quantified_business_metrics,
        "technical_readiness_level": str(technical_readiness_level).upper(),
        "target_timeline_weeks": target_timeline_weeks,
    }
    is_valid, err_msg = validate_tool_arguments(
        "evaluate_deal_qualification_criteria", raw_args
    )
    if not is_valid:
        return {
            "status": "ERROR",
            "error_code": "INVALID_QUALIFICATION_INPUT",
            "message": str(err_msg),
            "recovery_instruction": (
                "Re-invoke `evaluate_deal_qualification_criteria` with valid arguments: "
                "`estimated_deal_value_usd` must be > 0, `technical_readiness_level` must be "
                "'LOW', 'MEDIUM', or 'HIGH', and `target_timeline_weeks` must be between 1 and 52."
            ),
        }

    try:
        validated = DealQualificationInputSchema(**raw_args)
        risks: List[str] = []

        # 1. Business Metrics (0-20)
        metrics_text = validated.quantified_business_metrics.strip()
        if len(metrics_text) >= 25 and any(ch.isdigit() or ch in "%$" for ch in metrics_text):
            metrics_score = 20
        elif len(metrics_text) >= 10:
            metrics_score = 12
            risks.append("Business metrics are qualitative; quantify target ROI or KPI percentage.")
        else:
            metrics_score = 4
            risks.append("Missing quantified business value or success metrics.")

        # 2. Executive Sponsor (0-20)
        if validated.executive_sponsor_identified:
            sponsor_score = 20
        else:
            sponsor_score = 5
            risks.append("No Executive Sponsor / Economic Buyer identified; high risk of stalled signature.")

        # 3. Technical Readiness (0-20)
        readiness_map = {"HIGH": 20, "MEDIUM": 15, "LOW": 8}
        tech_score = readiness_map.get(validated.technical_readiness_level, 12)
        if validated.technical_readiness_level == "LOW":
            risks.append("Low technical/data readiness; customer requires foundational cloud & data governance first.")

        # 4. Budget Confirmed (0-20)
        if validated.budget_confirmed:
            budget_score = 20
        else:
            budget_score = 6
            risks.append("Customer budget is unconfirmed; verify funding allocation before committing delivery pod.")

        # 5. Timeline Realism (0-20)
        if validated.target_timeline_weeks >= 4:
            timeline_score = 20
        else:
            timeline_score = 8
            risks.append(
                f"Requested timeline ({validated.target_timeline_weeks} weeks) is shorter than standard 4-week minimum staffing lead time."
            )

        total_score = (
            metrics_score + sponsor_score + tech_score + budget_score + timeline_score
        )

        if total_score >= 70:
            qual_status = "QUALIFIED_READY_FOR_PROPOSAL"
        elif total_score >= 45:
            qual_status = "NEEDS_DISCOVERY_REFINEMENT"
        else:
            qual_status = "DISQUALIFIED_HIGH_RISK"

        # Recommend engagement tier
        if validated.estimated_deal_value_usd >= 500000 or validated.target_timeline_weeks >= 12:
            rec_tier = "tier_3_enterprise_scale"
        elif validated.estimated_deal_value_usd >= 250000 or validated.target_timeline_weeks >= 8:
            rec_tier = "tier_2_pilot_mvp"
        else:
            rec_tier = "tier_1_discovery_sprint"

        # If deal needs refinement and is low readiness, default to discovery sprint
        if qual_status == "NEEDS_DISCOVERY_REFINEMENT" and validated.technical_readiness_level == "LOW":
            rec_tier = "tier_1_discovery_sprint"

        output = DealQualificationOutputSchema(
            status="SUCCESS",
            customer_name=validated.customer_name,
            opportunity_name=validated.opportunity_name,
            qualification_score=total_score,
            qualification_status=qual_status,
            recommended_tier=rec_tier,
            dimension_breakdown={
                "business_metrics": metrics_score,
                "executive_sponsor": sponsor_score,
                "technical_readiness": tech_score,
                "budget_confirmed": budget_score,
                "timeline_realism": timeline_score,
            },
            identified_risks_and_gaps=risks,
            next_step_guidance=(
                f"Opportunity scored {total_score}/100 ({qual_status}). Proceed with "
                f"'{rec_tier}' template and resource sizing."
            ),
        )
        return output.model_dump()
    except Exception as exc:
        return {
            "status": "ERROR",
            "error_code": "QUALIFICATION_EXECUTION_ERROR",
            "message": str(exc),
            "recovery_instruction": (
                "Inspect input types for `evaluate_deal_qualification_criteria` and retry with "
                "valid boolean flags for `executive_sponsor_identified` and `budget_confirmed`."
            ),
        }


def calculate_delivery_resource_estimate(
    recommended_tier: str,
    custom_duration_weeks: Optional[int] = None,
    requested_discount_pct: float = 0.0,
) -> Dict[str, Any]:
    """Calculates delivery pod staffing, billable hours, list price, net price, and HITL flags.

    Args:
        recommended_tier: Engagement tier key ('tier_1_discovery_sprint',
            'tier_2_pilot_mvp', or 'tier_3_enterprise_scale').
        custom_duration_weeks: Optional override for engagement duration in weeks (2 to 52).
        requested_discount_pct: Requested commercial discount percentage (0.0 to 50.0).

    Returns:
        Dict[str, Any]: Resource sizing and commercial estimate containing:
            - status (str): 'SUCCESS' or 'ERROR'.
            - duration_weeks (int): Engagement duration in weeks.
            - staffing_pod (List[Dict]): Role breakdown with FTE, hours, and subtotal.
            - total_hours (int): Total billable engineering and delivery hours.
            - list_price_usd (float): Gross price including 5% delivery contingency.
            - discount_pct (float): Applied discount percentage.
            - net_price_usd (float): Final customer net price in USD.
            - requires_hitl_approval (bool): True if net_price_usd >= $500,000 or discount > 15%.
            - hitl_trigger_reasons (List[str]): Reasons human approval is required.
            - recovery_instruction (str, optional): Guided recovery instructions if an error occurs.
    """
    raw_args: Dict[str, Any] = {
        "recommended_tier": recommended_tier,
        "requested_discount_pct": requested_discount_pct,
    }
    if custom_duration_weeks is not None:
        raw_args["custom_duration_weeks"] = custom_duration_weeks

    is_valid, err_msg = validate_tool_arguments(
        "calculate_delivery_resource_estimate", raw_args
    )
    if not is_valid:
        return {
            "status": "ERROR",
            "error_code": "INVALID_RESOURCE_ESTIMATE_INPUT",
            "message": str(err_msg),
            "recovery_instruction": (
                "Pass `recommended_tier` as one of 'tier_1_discovery_sprint', "
                "'tier_2_pilot_mvp', or 'tier_3_enterprise_scale', and keep "
                "`requested_discount_pct` between 0.0 and 50.0."
            ),
        }

    try:
        validated = ResourceEstimateInputSchema(**raw_args)
        tmpl = DEFAULT_PROPOSAL_TEMPLATES[validated.recommended_tier]
        weeks = validated.custom_duration_weeks or tmpl["recommended_duration_weeks"]

        pod_breakdown = []
        total_hours = 0
        raw_labor_cost = 0.0

        for role_spec in tmpl["default_pod_roles"]:
            role_hours = int(round(role_spec["fte"] * 40 * weeks))
            role_total = round(role_hours * role_spec["hourly_rate"], 2)
            total_hours += role_hours
            raw_labor_cost += role_total
            pod_breakdown.append(
                {
                    "role": role_spec["role"],
                    "fte": role_spec["fte"],
                    "hourly_rate_usd": role_spec["hourly_rate"],
                    "billable_hours": role_hours,
                    "role_subtotal_usd": role_total,
                }
            )

        # Standard 5% delivery contingency
        contingency_usd = round(raw_labor_cost * 0.05, 2)
        list_price_usd = round(raw_labor_cost + contingency_usd, 2)
        discount_amount_usd = round(
            list_price_usd * (validated.requested_discount_pct / 100.0), 2
        )
        net_price_usd = round(list_price_usd - discount_amount_usd, 2)

        hitl_reasons = []
        if net_price_usd >= 500000:
            hitl_reasons.append(
                f"Net contract value (${net_price_usd:,.2f}) meets or exceeds the $500,000 executive approval threshold."
            )
        if validated.requested_discount_pct > 15.0:
            hitl_reasons.append(
                f"Requested commercial discount ({validated.requested_discount_pct}%) exceeds the 15.0% standard delegation limit."
            )

        return {
            "status": "SUCCESS",
            "recommended_tier": validated.recommended_tier,
            "duration_weeks": weeks,
            "staffing_pod": pod_breakdown,
            "total_hours": total_hours,
            "contingency_pct": 5.0,
            "list_price_usd": list_price_usd,
            "discount_pct": validated.requested_discount_pct,
            "discount_amount_usd": discount_amount_usd,
            "net_price_usd": net_price_usd,
            "requires_hitl_approval": len(hitl_reasons) > 0,
            "hitl_trigger_reasons": hitl_reasons,
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "error_code": "RESOURCE_CALCULATION_ERROR",
            "message": str(exc),
            "recovery_instruction": (
                "Retry `calculate_delivery_resource_estimate` using a valid tier key and "
                "numeric discount percentage."
            ),
        }


def retrieve_proposal_template_by_tier(tier_key: str) -> Dict[str, Any]:
    """Retrieves the standardized Statement of Work (SOW) proposal template from persistent storage.

    Args:
        tier_key: Engagement tier identifier ('tier_1_discovery_sprint',
            'tier_2_pilot_mvp', or 'tier_3_enterprise_scale').

    Returns:
        Dict[str, Any]: Template payload containing:
            - status (str): 'SUCCESS' or 'ERROR'.
            - template (Dict[str, Any]): Structured SOW sections, phases, deliverables, and roles.
            - recovery_instruction (str, optional): Guided instructions if `tier_key` is unknown.
    """
    is_valid, err_msg = validate_tool_arguments(
        "retrieve_proposal_template_by_tier", {"tier_key": tier_key}
    )
    if not is_valid:
        return {
            "status": "ERROR",
            "error_code": "UNKNOWN_TEMPLATE_TIER",
            "message": str(err_msg),
            "recovery_instruction": (
                "Call `retrieve_proposal_template_by_tier` with one of the supported tier keys: "
                "'tier_1_discovery_sprint', 'tier_2_pilot_mvp', or 'tier_3_enterprise_scale'."
            ),
        }

    template = global_memory_store.get_template(tier_key)
    if not template:
        template = DEFAULT_PROPOSAL_TEMPLATES.get(tier_key)

    return {
        "status": "SUCCESS",
        "tier_key": tier_key,
        "template": template,
    }


def generate_structured_proposal_draft(
    customer_name: str,
    opportunity_name: str,
    business_problem_summary: str,
    qualification_result: Dict[str, Any],
    resource_estimate: Dict[str, Any],
    template_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Synthesizes a complete, executive-ready Statement of Work (SOW) draft proposal from a template.

    Combines the customer's business context, MEDDPICC qualification scorecard, delivery pod
    sizing, scope phases, deliverables, and commercial pricing into a structured proposal document.

    Args:
        customer_name: Name of the customer organization.
        opportunity_name: Name of the opportunity or project.
        business_problem_summary: Summary of the customer's challenge and desired outcomes.
        qualification_result: Dictionary output from `evaluate_deal_qualification_criteria`.
        resource_estimate: Dictionary output from `calculate_delivery_resource_estimate`.
        template_payload: Dictionary output from `retrieve_proposal_template_by_tier`.

    Returns:
        Dict[str, Any]: Generated proposal package containing:
            - status (str): 'SUCCESS' or 'ERROR'.
            - proposal_title (str): Formal SOW title.
            - proposal_markdown (str): Complete formatted Statement of Work draft.
            - sections_included (List[str]): List of verified proposal sections.
            - recovery_instruction (str, optional): Recovery guidance if required inputs are missing.
    """
    raw_args = {
        "customer_name": customer_name,
        "opportunity_name": opportunity_name,
        "business_problem_summary": business_problem_summary,
        "qualification_result": qualification_result,
        "resource_estimate": resource_estimate,
        "template_payload": template_payload,
    }
    is_valid, err_msg = validate_tool_arguments(
        "generate_structured_proposal_draft", raw_args
    )
    if not is_valid:
        return {
            "status": "ERROR",
            "error_code": "INVALID_PROPOSAL_DRAFT_INPUT",
            "message": str(err_msg),
            "recovery_instruction": (
                "Ensure `qualification_result`, `resource_estimate`, and `template_payload` are "
                "passed as dictionary objects from earlier tool steps, and `business_problem_summary` "
                "is at least 10 characters."
            ),
        }

    try:
        validated = ProposalDraftInputSchema(**raw_args)
        tmpl = validated.template_payload.get("template", validated.template_payload)
        if not tmpl or "title" not in tmpl:
            tmpl = DEFAULT_PROPOSAL_TEMPLATES["tier_2_pilot_mvp"]

        exec_summary = tmpl["executive_summary_template"].format(
            customer_name=validated.customer_name,
            opportunity_name=validated.opportunity_name,
        )

        qual_score = validated.qualification_result.get("qualification_score", 0)
        qual_status = validated.qualification_result.get("qualification_status", "UNKNOWN")
        risks = validated.qualification_result.get("identified_risks_and_gaps", [])

        weeks = validated.resource_estimate.get("duration_weeks", tmpl["recommended_duration_weeks"])
        total_hours = validated.resource_estimate.get("total_hours", 0)
        list_price = validated.resource_estimate.get("list_price_usd", 0.0)
        discount_pct = validated.resource_estimate.get("discount_pct", 0.0)
        net_price = validated.resource_estimate.get("net_price_usd", 0.0)
        pod_roles = validated.resource_estimate.get("staffing_pod", [])

        phases_lines = "\n".join(f"- {phase}" for phase in tmpl.get("scope_phases", []))
        deliverables_lines = "\n".join(
            f"{idx}. {deliv}" for idx, deliv in enumerate(tmpl.get("deliverables", []), start=1)
        )

        pod_table_rows = []
        for role in pod_roles:
            pod_table_rows.append(
                f"| {role['role']} | {role['fte']} FTE | {role['billable_hours']} hrs | "
                f"${role['hourly_rate_usd']:,.2f}/hr | ${role['role_subtotal_usd']:,.2f} |"
            )
        pod_table_md = "\n".join(pod_table_rows)

        risk_lines = (
            "\n".join(f"- {r}" for r in risks)
            if risks
            else "- All primary qualification criteria satisfied with no critical blockers."
        )

        proposal_md = (
            f"# STATEMENT OF WORK (DRAFT PROPOSAL)\n"
            f"## Project: {validated.opportunity_name}\n"
            f"### Prepared For: {validated.customer_name}\n"
            f"### Engagement Tier: {tmpl['title']} ({weeks} Weeks)\n\n"
            f"---\n\n"
            f"## 1. Executive Summary & Business Context\n"
            f"{exec_summary}\n\n"
            f"Customer Challenge & Objectives:\n"
            f"{validated.business_problem_summary}\n\n"
            f"## 2. Deal Qualification & Readiness Scorecard\n"
            f"- Qualification Score: {qual_score} / 100 ({qual_status})\n"
            f"- Key Risks & Pre-Requisites:\n"
            f"{risk_lines}\n\n"
            f"## 3. Scope of Work & Delivery Phases ({weeks} Weeks)\n"
            f"{phases_lines}\n\n"
            f"## 4. Target Deliverables\n"
            f"{deliverables_lines}\n\n"
            f"## 5. Delivery Pod Staffing & Commercial Estimate\n"
            f"| Role | Allocation | Billable Hours | Rate (USD) | Subtotal (USD) |\n"
            f"| :--- | :--- | :--- | :--- | :--- |\n"
            f"{pod_table_md}\n\n"
            f"- Total Engineering & Delivery Hours: {total_hours} hrs\n"
            f"- Gross List Estimate (incl. 5% Contingency): ${list_price:,.2f}\n"
            f"- Applied Commercial Discount: {discount_pct:.1f}%\n"
            f"- Net Estimated Investment (USD): ${net_price:,.2f}\n\n"
            f"## 6. Key Assumptions & Governance\n"
            f"- Customer will provide timely access to subject matter experts, sandbox cloud environments, and sample datasets.\n"
            f"- Staffing lead time is subject to formal Statement of Work signature and pre-sales governance approval.\n"
        )

        return {
            "status": "SUCCESS",
            "proposal_title": f"{validated.customer_name} - {validated.opportunity_name} ({tmpl['title']})",
            "template_id": tmpl.get("template_id", "SOW-TMPL"),
            "proposal_markdown": proposal_md,
            "sections_included": [
                "Executive Summary & Business Context",
                "Deal Qualification & Readiness Scorecard",
                "Scope of Work & Delivery Phases",
                "Target Deliverables",
                "Delivery Pod Staffing & Commercial Estimate",
                "Key Assumptions & Governance",
            ],
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "error_code": "PROPOSAL_SYNTHESIS_ERROR",
            "message": str(exc),
            "recovery_instruction": (
                "Verify that `template_payload`, `qualification_result`, and `resource_estimate` "
                "contain valid outputs from the preceding tools and retry."
            ),
        }


ALL_ENTERPRISE_TOOLS = [
    evaluate_deal_qualification_criteria,
    calculate_delivery_resource_estimate,
    retrieve_proposal_template_by_tier,
    generate_structured_proposal_draft,
]
