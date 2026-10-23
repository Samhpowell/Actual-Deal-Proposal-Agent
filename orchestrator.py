"""Multi-Agent Orchestrator implementing Coordinator & Sequential ADK Patterns."""

import os
import time
from typing import Any, Dict, Optional

from .guardrails import (
    SecurityAndPolicyGuardrails,
    adk_before_model_guardrail_callback,
    adk_before_tool_policy_callback,
    global_guardrails,
)
from .hitl import HumanInTheLoopController, global_hitl_controller
from .memory_store import AgentMemoryStore, global_memory_store
from .prompts import (
    ENTERPRISE_AGENT_CONSTITUTION,
    PROPOSAL_SUBAGENT_INSTRUCTION,
    QUALIFICATION_SUBAGENT_INSTRUCTION,
    SIZING_SUBAGENT_INSTRUCTION,
)
from .router import StrategicModelRouter, global_model_router
from .tools import (
    calculate_delivery_resource_estimate,
    evaluate_deal_qualification_criteria,
    generate_structured_proposal_draft,
    retrieve_proposal_template_by_tier,
)
from .tracer import get_structured_logger

logger = get_structured_logger("Orchestrator")


class BaseSpecialistSubagent:
    """Base class for specialized ADK sub-agents."""

    def __init__(
        self,
        name: str,
        role: str,
        instruction: str,
        task_category: str,
        router: Optional[StrategicModelRouter] = None,
    ):
        self.name = name
        self.role = role
        self.instruction = instruction
        self.task_category = task_category
        self.router = router or global_model_router


class DealQualificationSpecialistAgent(BaseSpecialistSubagent):
    """Sub-Agent 1: Evaluates deal qualification criteria (MEDDPICC / BANT) and scores readiness."""

    def __init__(self):
        super().__init__(
            name="DealQualificationSpecialistAgent",
            role="Enterprise Deal Qualification & Risk Triage Specialist",
            instruction=QUALIFICATION_SUBAGENT_INSTRUCTION,
            task_category="FAST_TRIAGE",
        )

    def run(self, deal_input: Dict[str, Any]) -> Dict[str, Any]:
        route = self.router.route_task(self.task_category)
        logger.info(
            f"Running {self.name} with model {route['model_name']}",
            extra={"structured_data": {"agent": self.name, "model": route["model_name"]}},
        )

        result = evaluate_deal_qualification_criteria(
            customer_name=deal_input.get("customer_name", "Enterprise Client"),
            opportunity_name=deal_input.get("opportunity_name", "AI Initiative"),
            estimated_deal_value_usd=float(deal_input.get("estimated_deal_value_usd", 300000.0)),
            executive_sponsor_identified=bool(deal_input.get("executive_sponsor_identified", True)),
            budget_confirmed=bool(deal_input.get("budget_confirmed", True)),
            quantified_business_metrics=str(
                deal_input.get(
                    "quantified_business_metrics",
                    "Reduce manual triage cycle time by 40% and save $450k annually.",
                )
            ),
            technical_readiness_level=str(deal_input.get("technical_readiness_level", "HIGH")),
            target_timeline_weeks=int(deal_input.get("target_timeline_weeks", 8)),
        )

        if result.get("status") == "ERROR":
            fallback_weeks = max(4, min(52, int(deal_input.get("target_timeline_weeks", 8) or 8)))
            fallback_val = max(50000.0, float(deal_input.get("estimated_deal_value_usd", 250000.0) or 250000.0))
            result = evaluate_deal_qualification_criteria(
                customer_name=deal_input.get("customer_name") or "Enterprise Client",
                opportunity_name=deal_input.get("opportunity_name") or "AI Transformation",
                estimated_deal_value_usd=fallback_val,
                executive_sponsor_identified=bool(deal_input.get("executive_sponsor_identified", True)),
                budget_confirmed=bool(deal_input.get("budget_confirmed", True)),
                quantified_business_metrics=deal_input.get("quantified_business_metrics")
                or "Target 30% operational efficiency gain",
                technical_readiness_level="MEDIUM",
                target_timeline_weeks=fallback_weeks,
            )
            result["recovered_via_guided_error_handling"] = True

        result["routed_model"] = route["model_name"]
        result["subagent_name"] = self.name
        return result


class ResourceSizingSpecialistAgent(BaseSpecialistSubagent):
    """Sub-Agent 2: Calculates delivery staffing pod, hours, pricing, and HITL triggers."""

    def __init__(self):
        super().__init__(
            name="ResourceSizingSpecialistAgent",
            role="Delivery Pod Staffing & Commercial Estimator",
            instruction=SIZING_SUBAGENT_INSTRUCTION,
            task_category="FAST_TRIAGE",
        )

    def run(
        self,
        recommended_tier: str,
        custom_duration_weeks: Optional[int],
        requested_discount_pct: float,
    ) -> Dict[str, Any]:
        route = self.router.route_task(self.task_category)
        logger.info(
            f"Running {self.name} for tier {recommended_tier}",
            extra={"structured_data": {"agent": self.name, "tier": recommended_tier}},
        )

        result = calculate_delivery_resource_estimate(
            recommended_tier=recommended_tier,
            custom_duration_weeks=custom_duration_weeks,
            requested_discount_pct=requested_discount_pct,
        )
        result["routed_model"] = route["model_name"]
        result["subagent_name"] = self.name
        return result


class ProposalDraftingSpecialistAgent(BaseSpecialistSubagent):
    """Sub-Agent 3: Retrieves SOW template and drafts tailored executive proposal using Gemini Pro tier."""

    def __init__(self):
        super().__init__(
            name="ProposalDraftingSpecialistAgent",
            role="Executive Statement of Work (SOW) Proposal Author",
            instruction=PROPOSAL_SUBAGENT_INSTRUCTION,
            task_category="COMPLEX_PROPOSAL_SYNTHESIS",
        )

    def run(
        self,
        customer_name: str,
        opportunity_name: str,
        business_problem_summary: str,
        qualification_result: Dict[str, Any],
        resource_estimate: Dict[str, Any],
    ) -> Dict[str, Any]:
        tier_key = qualification_result.get("recommended_tier", "tier_2_pilot_mvp")
        route = self.router.route_task(
            self.task_category, payload_size=len(business_problem_summary) * 20
        )
        logger.info(
            f"Running {self.name} with model {route['model_name']}",
            extra={"structured_data": {"agent": self.name, "model": route["model_name"]}},
        )

        tmpl_res = retrieve_proposal_template_by_tier(tier_key=tier_key)
        draft_res = generate_structured_proposal_draft(
            customer_name=customer_name,
            opportunity_name=opportunity_name,
            business_problem_summary=business_problem_summary,
            qualification_result=qualification_result,
            resource_estimate=resource_estimate,
            template_payload=tmpl_res,
        )
        draft_res["routed_model"] = route["model_name"]
        draft_res["subagent_name"] = self.name
        return draft_res


class EnterpriseDealCoordinatorAgent:
    """Root Coordinator Agent orchestrating the 3 specialized sub-agents, guardrails, and HITL."""

    def __init__(
        self,
        memory: Optional[AgentMemoryStore] = None,
        guardrails: Optional[SecurityAndPolicyGuardrails] = None,
        hitl: Optional[HumanInTheLoopController] = None,
        router: Optional[StrategicModelRouter] = None,
    ):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.memory = memory or global_memory_store
        self.guardrails = guardrails or global_guardrails
        self.hitl = hitl or global_hitl_controller
        self.router = router or global_model_router

        self.qualification_agent = DealQualificationSpecialistAgent()
        self.sizing_agent = ResourceSizingSpecialistAgent()
        self.proposal_agent = ProposalDraftingSpecialistAgent()

    def evaluate_and_draft_proposal(
        self,
        deal_request: Dict[str, Any],
        session_id: str = "default_session",
    ) -> Dict[str, Any]:
        """Executes the end-to-end Coordinator -> Sequential Sub-Agent workflow."""
        start_time = time.perf_counter()

        customer_name = str(deal_request.get("customer_name", "Acme Corporation"))
        opportunity_name = str(
            deal_request.get("opportunity_name", "Enterprise Customer Operations AI Agent")
        )
        business_problem = str(
            deal_request.get(
                "business_problem_summary",
                deal_request.get(
                    "quantified_business_metrics",
                    "Automate enterprise ticket triage and knowledge retrieval to reduce resolution time by 35%.",
                ),
            )
        )
        user_prompt_summary = f"Qualify {customer_name} - {opportunity_name}: {business_problem}"

        # 1. Pre-execution Input Security Guardrail
        input_ok, input_err = self.guardrails.validate_user_input(user_prompt_summary)
        if not input_ok:
            return {
                "status": "BLOCKED_BY_GUARDRAIL",
                "error_code": "SECURITY_GUARDRAIL_BLOCK",
                "message": input_err,
            }

        # 2. Commercial Policy Guardrail
        deal_val = float(deal_request.get("estimated_deal_value_usd", 320000.0))
        discount_pct = float(deal_request.get("requested_discount_pct", 0.0))
        policy_ok, policy_err = self.guardrails.validate_commercial_policy(
            deal_val, discount_pct
        )
        if not policy_ok:
            return {
                "status": "BLOCKED_BY_GUARDRAIL",
                "error_code": "COMMERCIAL_POLICY_BLOCK",
                "message": policy_err,
            }

        self.memory.save_message(session_id, "user", user_prompt_summary)

        # 3. Stage 1 Sub-Agent: Qualification Criteria Check
        qual_result = self.qualification_agent.run(deal_input=deal_request)

        # 4. Stage 2 Sub-Agent: Delivery Resource & Commercial Sizing
        custom_weeks = deal_request.get("custom_duration_weeks")
        sizing_result = self.sizing_agent.run(
            recommended_tier=qual_result.get("recommended_tier", "tier_2_pilot_mvp"),
            custom_duration_weeks=int(custom_weeks) if custom_weeks else None,
            requested_discount_pct=discount_pct,
        )

        # 5. Stage 3 Sub-Agent: Retrieve SOW Template & Draft Proposal
        proposal_result = self.proposal_agent.run(
            customer_name=customer_name,
            opportunity_name=opportunity_name,
            business_problem_summary=business_problem,
            qualification_result=qual_result,
            resource_estimate=sizing_result,
        )

        proposal_md = proposal_result.get("proposal_markdown", "")

        # 6. Post-Execution Self-Evaluation Guardrail Check
        self_eval_report = self.guardrails.evaluate_proposal_quality(
            proposal_markdown=proposal_md,
            customer_name=customer_name,
        )

        # 7. Human-in-the-Loop (HITL) Confirmation Hook for High-Stakes Deals
        net_price = float(sizing_result.get("net_price_usd", 0.0))
        needs_hitl, hitl_reasons = self.hitl.requires_human_approval(
            net_price_usd=net_price,
            discount_pct=discount_pct,
            qualification_status=qual_result.get("qualification_status", ""),
        )
        hitl_record = None
        hitl_status = "AUTO_APPROVED_STANDARD_DEAL"
        if needs_hitl:
            hitl_record = self.hitl.queue_for_human_approval(
                customer_name=customer_name,
                opportunity_name=opportunity_name,
                net_price_usd=net_price,
                discount_pct=discount_pct,
                reasons=hitl_reasons,
                proposal_preview=proposal_md,
            )
            hitl_status = "PENDING_HUMAN_APPROVAL"

        # 8. Persist Proposal & Session Context
        saved_proposal_id = self.memory.save_deal_proposal(
            {
                "session_id": session_id,
                "customer_name": customer_name,
                "opportunity_name": opportunity_name,
                "qualification_score": qual_result.get("qualification_score", 0),
                "qualification_status": qual_result.get("qualification_status", ""),
                "recommended_tier": qual_result.get("recommended_tier", ""),
                "net_price_usd": net_price,
                "hitl_status": hitl_status,
                "proposal_markdown": proposal_md,
            }
        )

        assistant_summary = (
            f"Completed deal qualification ({qual_result.get('qualification_score')}/100 - "
            f"{qual_result.get('qualification_status')}) and generated SOW draft '{saved_proposal_id}' "
            f"using template '{proposal_result.get('template_id')}' (Net: ${net_price:,.2f}, HITL: {hitl_status})."
        )
        self.memory.save_message(session_id, "assistant", assistant_summary)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return {
            "status": "SUCCESS",
            "proposal_id": saved_proposal_id,
            "execution_time_ms": elapsed_ms,
            "orchestration_topology": "ADK Coordinator + 3-Stage Sequential Specialist Sub-Agents",
            "model_routing_summary": {
                "qualification_model": qual_result.get("routed_model"),
                "sizing_model": sizing_result.get("routed_model"),
                "proposal_synthesis_model": proposal_result.get("routed_model"),
            },
            "qualification": qual_result,
            "resource_estimate": sizing_result,
            "proposal": proposal_result,
            "self_evaluation": self_eval_report,
            "hitl_governance": {
                "requires_human_approval": needs_hitl,
                "hitl_status": hitl_status,
                "trigger_reasons": hitl_reasons,
                "approval_request": hitl_record,
            },
        }


def build_adk_agent_hierarchy() -> Any:
    """Constructs the Google ADK Coordinator and Sequential Sub-Agent hierarchy."""
    try:
        from google.adk.agents import LlmAgent, SequentialAgent
        from google.adk.tools import FunctionTool

        qual_subagent = LlmAgent(
            name="deal_qualification_specialist",
            model="gemini-2.5-flash",
            description="Evaluates enterprise deal qualification criteria (MEDDPICC/BANT) and scores readiness.",
            instruction=QUALIFICATION_SUBAGENT_INSTRUCTION,
            tools=[FunctionTool(func=evaluate_deal_qualification_criteria)],
            before_model_callback=adk_before_model_guardrail_callback,
            before_tool_callback=adk_before_tool_policy_callback,
        )

        sizing_subagent = LlmAgent(
            name="resource_sizing_specialist",
            model="gemini-2.5-flash",
            description="Calculates delivery pod FTEs, billable hours, commercial pricing, and HITL flags.",
            instruction=SIZING_SUBAGENT_INSTRUCTION,
            tools=[FunctionTool(func=calculate_delivery_resource_estimate)],
            before_tool_callback=adk_before_tool_policy_callback,
        )

        proposal_subagent = LlmAgent(
            name="proposal_drafting_specialist",
            model="gemini-2.5-pro",
            description="Retrieves SOW templates and authors executive Statement of Work proposals.",
            instruction=PROPOSAL_SUBAGENT_INSTRUCTION,
            tools=[
                FunctionTool(func=retrieve_proposal_template_by_tier),
                FunctionTool(func=generate_structured_proposal_draft),
            ],
        )

        sequential_pipeline = SequentialAgent(
            name="qualification_to_proposal_pipeline",
            description="Sequential pipeline executing deal qualification, resource sizing, and SOW drafting.",
            sub_agents=[qual_subagent, sizing_subagent, proposal_subagent],
        )

        coordinator = LlmAgent(
            name="enterprise_deal_proposal_coordinator",
            model="gemini-2.5-pro",
            description="Root Coordinator Agent for enterprise deal qualification and SOW proposal generation.",
            instruction=ENTERPRISE_AGENT_CONSTITUTION,
            sub_agents=[sequential_pipeline],
            before_model_callback=adk_before_model_guardrail_callback,
        )
        return coordinator
    except Exception:
        return EnterpriseDealCoordinatorAgent()


global_coordinator_agent = EnterpriseDealCoordinatorAgent()
root_agent = build_adk_agent_hierarchy()
