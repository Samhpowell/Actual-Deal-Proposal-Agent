"""Human-in-the-Loop (HITL) Confirmation Gate Module.

Implements explicit execution stops requiring human review and approval before
finalizing high-value proposals (Net Price >= $500,000) or non-standard commercial
discounts (Discount > 15%).
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple


class HumanInTheLoopController:
    """Manages pending human approval requests for high-stakes commercial proposals."""

    def __init__(self):
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.approved_records: Dict[str, Dict[str, Any]] = {}
        self.rejected_records: Dict[str, Dict[str, Any]] = {}

    def requires_human_approval(
        self, net_price_usd: float, discount_pct: float, qualification_status: str = ""
    ) -> Tuple[bool, List[str]]:
        """Determines whether a proposal must pause for human executive approval."""
        reasons: List[str] = []
        if net_price_usd >= 500000.0:
            reasons.append(
                f"High-Value Deal Gate: Net investment (${net_price_usd:,.2f}) is >= $500,000."
            )
        if discount_pct > 15.0:
            reasons.append(
                f"Discount Delegation Gate: Requested discount ({discount_pct:.1f}%) exceeds 15.0% self-approval limit."
            )
        if qualification_status == "DISQUALIFIED_HIGH_RISK":
            reasons.append(
                "Qualification Risk Gate: Opportunity is flagged as DISQUALIFIED_HIGH_RISK."
            )
        return len(reasons) > 0, reasons

    def queue_for_human_approval(
        self,
        customer_name: str,
        opportunity_name: str,
        net_price_usd: float,
        discount_pct: float,
        reasons: List[str],
        proposal_preview: str,
    ) -> Dict[str, Any]:
        """Creates a pending HITL approval request and pauses external proposal release."""
        approval_id = f"HITL-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "approval_id": approval_id,
            "customer_name": customer_name,
            "opportunity_name": opportunity_name,
            "net_price_usd": net_price_usd,
            "discount_pct": discount_pct,
            "trigger_reasons": reasons,
            "status": "PENDING_HUMAN_APPROVAL",
            "proposal_preview_snippet": (proposal_preview or "")[:300],
            "created_at": time.time(),
        }
        self.pending_approvals[approval_id] = record
        return record

    def approve_request(
        self,
        approval_id: str,
        approver_role: str = "Practice_Director",
        comments: str = "Commercial terms and delivery pod approved.",
    ) -> Optional[Dict[str, Any]]:
        """Approves a paused HITL proposal request so it can be released."""
        if approval_id not in self.pending_approvals:
            return None
        record = self.pending_approvals.pop(approval_id)
        record["status"] = "APPROVED_BY_HUMAN"
        record["approved_by"] = approver_role
        record["approver_comments"] = comments
        record["reviewed_at"] = time.time()
        self.approved_records[approval_id] = record
        return record

    def reject_request(
        self,
        approval_id: str,
        approver_role: str = "Practice_Director",
        reason: str = "Requires executive sponsor sign-off and reduced discount.",
    ) -> Optional[Dict[str, Any]]:
        """Rejects a paused HITL proposal request."""
        if approval_id not in self.pending_approvals:
            return None
        record = self.pending_approvals.pop(approval_id)
        record["status"] = "REJECTED_BY_HUMAN"
        record["reviewed_by"] = approver_role
        record["rejection_reason"] = reason
        record["reviewed_at"] = time.time()
        self.rejected_records[approval_id] = record
        return record

    def list_pending(self) -> List[Dict[str, Any]]:
        return list(self.pending_approvals.values())


global_hitl_controller = HumanInTheLoopController()
