"""Interactive Command-Line Interface for the Enterprise Deal Qualification & Proposal Agent."""

import argparse
import json
import sys
from agent_app.orchestrator import global_coordinator_agent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enterprise Deal Qualification & SOW Proposal Drafting Agent CLI"
    )
    parser.add_argument("--customer", default="Global Manufacturing Corp", help="Customer organization name")
    parser.add_argument(
        "--opportunity",
        default="Supply Chain Predictive Maintenance & Triage Agent",
        help="Opportunity title",
    )
    parser.add_argument("--value", type=float, default=380000.0, help="Estimated deal value in USD")
    parser.add_argument(
        "--sponsor",
        action="store_true",
        default=True,
        help="Whether an Executive Sponsor (VP/C-Level) is confirmed",
    )
    parser.add_argument(
        "--budget",
        action="store_true",
        default=True,
        help="Whether customer budget is confirmed",
    )
    parser.add_argument(
        "--metrics",
        default="Reduce unplanned factory downtime by 25% and save $1.8M annually across 4 plants.",
        help="Quantified business KPIs and ROI metrics",
    )
    parser.add_argument(
        "--readiness",
        default="HIGH",
        choices=["LOW", "MEDIUM", "HIGH"],
        help="Customer technical & data readiness level",
    )
    parser.add_argument("--weeks", type=int, default=8, help="Target delivery duration in weeks")
    parser.add_argument("--discount", type=float, default=5.0, help="Requested discount percentage (0-50)")
    parser.add_argument("--json", action="store_true", help="Print full structured JSON output")
    args = parser.parse_args()

    result = global_coordinator_agent.evaluate_and_draft_proposal(
        {
            "customer_name": args.customer,
            "opportunity_name": args.opportunity,
            "estimated_deal_value_usd": args.value,
            "executive_sponsor_identified": args.sponsor,
            "budget_confirmed": args.budget,
            "quantified_business_metrics": args.metrics,
            "business_problem_summary": args.metrics,
            "technical_readiness_level": args.readiness,
            "target_timeline_weeks": args.weeks,
            "requested_discount_pct": args.discount,
        }
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    if result.get("status") != "SUCCESS":
        print(f"Blocked: {result.get('message')}", file=sys.stderr)
        sys.exit(1)

    qual = result["qualification"]
    est = result["resource_estimate"]
    hitl = result["hitl_governance"]
    print("=" * 78)
    print(f"DEAL QUALIFICATION & PROPOSAL SUMMARY ({result['proposal_id']})")
    print("=" * 78)
    print(f"Customer:             {qual['customer_name']}")
    print(f"Opportunity:          {qual['opportunity_name']}")
    print(f"Qualification Score:  {qual['qualification_score']} / 100 ({qual['qualification_status']})")
    print(f"Recommended Tier:     {qual['recommended_tier']}")
    print(f"Estimated Investment: ${est['net_price_usd']:,.2f} ({est['duration_weeks']} weeks, {est['total_hours']} hrs)")
    print(f"HITL Governance:      {hitl['hitl_status']}")
    print("-" * 78)
    print(result["proposal"]["proposal_markdown"])


if __name__ == "__main__":
    main()
