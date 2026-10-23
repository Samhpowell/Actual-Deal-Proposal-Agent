"""Persistent SQLite Session State and Conversation History Compaction."""

import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from .prompts import ENTERPRISE_AGENT_CONSTITUTION

DEFAULT_PROPOSAL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "tier_1_discovery_sprint": {
        "template_id": "SOW-TMPL-TIER1-DISCOVERY",
        "tier_key": "tier_1_discovery_sprint",
        "title": "4-Week Enterprise AI Strategy & Architecture Discovery Sprint",
        "recommended_duration_weeks": 4,
        "target_deal_range": "Up to $250,000",
        "executive_summary_template": (
            "This Statement of Work defines a 4-week Enterprise AI Strategy & Discovery Sprint for "
            "{customer_name} focused on '{opportunity_name}'. The engagement validates high-value "
            "business use cases, establishes cloud security and data readiness, and produces a "
            "board-ready implementation roadmap."
        ),
        "scope_phases": [
            "Phase 1 (Week 1): Executive Alignment, Use Case Value Mapping & Data Audit",
            "Phase 2 (Weeks 2-3): Target Cloud Architecture, Security Guardrails & Feasibility Prototype",
            "Phase 3 (Week 4): Production Roadmap, ROI Business Case & Executive Readout",
        ],
        "deliverables": [
            "Prioritized AI Use Case Scorecard & Business Value Model",
            "Target Cloud Reference Architecture & Data Governance Blueprint",
            "Production Delivery Roadmap & Resource Plan",
        ],
        "default_pod_roles": [
            {"role": "Technical Delivery Lead", "fte": 0.5, "hourly_rate": 350},
            {"role": "Principal Cloud AI Architect", "fte": 1.0, "hourly_rate": 375},
            {"role": "Data Readiness Consultant", "fte": 0.5, "hourly_rate": 300},
        ],
    },
    "tier_2_pilot_mvp": {
        "template_id": "SOW-TMPL-TIER2-PILOT",
        "tier_key": "tier_2_pilot_mvp",
        "title": "8-Week Enterprise AI Rapid Prototype & Pilot MVP Sprint",
        "recommended_duration_weeks": 8,
        "target_deal_range": "$250,000 to $499,999",
        "executive_summary_template": (
            "This Statement of Work outlines an 8-week Rapid Prototype & Pilot MVP engagement for "
            "{customer_name} to design, build, and evaluate '{opportunity_name}'. The joint delivery "
            "pod will deploy a working pilot agent connected to enterprise data sources with "
            "automated evaluation benchmarks and security guardrails."
        ),
        "scope_phases": [
            "Phase 1 (Weeks 1-2): Architecture Finalization, Data Ingestion & Evaluation Golden Dataset",
            "Phase 2 (Weeks 3-6): Multi-Agent Orchestration Build, Tool Integration & Safety Guardrails",
            "Phase 3 (Weeks 7-8): Pilot User Acceptance Testing, Telemetry Tuning & Production Handover",
        ],
        "deliverables": [
            "Deployed Pilot MVP Agent in Customer Cloud Environment",
            "Automated Golden Dataset Evaluation Suite & Benchmark Report",
            "Operational Runbook, Telemetry Dashboard & Production Scaling Plan",
        ],
        "default_pod_roles": [
            {"role": "Technical Delivery Lead", "fte": 1.0, "hourly_rate": 350},
            {"role": "Lead AI Agent Engineer", "fte": 1.0, "hourly_rate": 350},
            {"role": "Data & RAG Integration Engineer", "fte": 1.0, "hourly_rate": 325},
        ],
    },
    "tier_3_enterprise_scale": {
        "template_id": "SOW-TMPL-TIER3-SCALE",
        "tier_key": "tier_3_enterprise_scale",
        "title": "12-Week Enterprise Production AI Transformation Program",
        "recommended_duration_weeks": 12,
        "target_deal_range": "$500,000+",
        "executive_summary_template": (
            "This Statement of Work establishes a 12-week Enterprise Production Transformation "
            "Program for {customer_name} delivering '{opportunity_name}' at production scale. "
            "The program encompasses full multi-agent orchestration, enterprise integration, "
            "Human-in-the-Loop controls, and operational readiness."
        ),
        "scope_phases": [
            "Phase 1 (Weeks 1-3): Enterprise Landing Zone, Security Compliance & Architecture Sign-Off",
            "Phase 2 (Weeks 4-8): Production Multi-Agent Development, Enterprise API & RAG Integration",
            "Phase 3 (Weeks 9-10): Load Testing, Guardrail Verification & HITL Workflows",
            "Phase 4 (Weeks 11-12): Production Rollout, Center of Excellence Enablement & Hypercare",
        ],
        "deliverables": [
            "Production Multi-Agent Application with Automated Evaluation Suite",
            "Enterprise Governance & Human-in-the-Loop Approval Framework",
            "Executive ROI Realization Report & Customer Engineering Enablement Package",
        ],
        "default_pod_roles": [
            {"role": "Engagement Director / Technical Delivery Lead", "fte": 1.0, "hourly_rate": 375},
            {"role": "Principal AI Systems Architect", "fte": 1.0, "hourly_rate": 375},
            {"role": "Senior AI Agent Engineer", "fte": 2.0, "hourly_rate": 340},
            {"role": "Cloud Platform & Security Engineer", "fte": 1.0, "hourly_rate": 330},
        ],
    },
}


class AgentMemoryStore:
    """Manages SQLite session state, proposal templates, and conversation history compaction."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self._init_db()
        self._seed_templates()

    def _get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    tokens_estimated INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT,
                    compacted_turns_count INTEGER DEFAULT 0,
                    updated_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_templates (
                    tier_key TEXT PRIMARY KEY,
                    template_id TEXT,
                    title TEXT,
                    payload_json TEXT,
                    updated_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deal_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    customer_name TEXT,
                    opportunity_name TEXT,
                    qualification_score INTEGER,
                    qualification_status TEXT,
                    recommended_tier TEXT,
                    net_price_usd REAL,
                    hitl_status TEXT,
                    proposal_markdown TEXT,
                    details_json TEXT,
                    created_at REAL
                )
                """
            )
            conn.commit()

    def _seed_templates(self) -> None:
        with self._get_connection() as conn:
            for tier_key, tmpl in DEFAULT_PROPOSAL_TEMPLATES.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO proposal_templates (tier_key, template_id, title, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (tier_key, tmpl["template_id"], tmpl["title"], json.dumps(tmpl), time.time()),
                )
            conn.commit()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(str(text)) // 4)

    def save_message(
        self, session_id: str, role: str, content: str, max_tokens: int = 800
    ) -> None:
        """Stores a conversation message and compacts history if token limit is exceeded."""
        tokens = self.estimate_tokens(content)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO conversation_history (session_id, role, content, timestamp, tokens_estimated) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, time.time(), tokens),
            )
            conn.commit()
        self.compact_session_history(session_id, max_tokens=max_tokens)

    def compact_session_history(
        self, session_id: str, max_tokens: int = 800, preserve_recent: int = 4
    ) -> bool:
        """Compacts older conversation turns into a rolling summary when token threshold is exceeded."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, role, content, tokens_estimated FROM conversation_history WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        if len(rows) <= preserve_recent:
            return False

        total_tokens = sum(r.get("tokens_estimated", 0) for r in rows)
        if total_tokens <= max_tokens:
            return False

        older_turns = rows[:-preserve_recent]
        older_ids = [r["id"] for r in older_turns]
        summary_snippets = []
        for turn in older_turns:
            speaker = "User" if turn["role"] == "user" else "Agent"
            snippet = turn["content"][:90] + ("..." if len(turn["content"]) > 90 else "")
            summary_snippets.append(f"[{speaker}: {snippet}]")

        delta_summary = " | ".join(summary_snippets)

        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT summary, compacted_turns_count FROM session_summaries WHERE session_id = ?",
                (session_id,),
            )
            existing = cursor.fetchone()
            if existing and existing["summary"]:
                merged_summary = f"{existing['summary']} | {delta_summary}"
                compacted_count = int(existing["compacted_turns_count"]) + len(older_ids)
            else:
                merged_summary = delta_summary
                compacted_count = len(older_ids)

            if len(merged_summary) > 1000:
                merged_summary = "..." + merged_summary[-997:]

            conn.execute(
                """
                INSERT OR REPLACE INTO session_summaries (session_id, summary, compacted_turns_count, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, merged_summary, compacted_count, time.time()),
            )
            placeholders = ",".join("?" * len(older_ids))
            conn.execute(
                f"DELETE FROM conversation_history WHERE id IN ({placeholders})",
                older_ids,
            )
            conn.commit()
        return True

    def get_conversation_history(
        self, session_id: str, limit: int = 20, include_constitution: bool = True
    ) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = []
        if include_constitution:
            history.append(
                {"role": "system", "content": ENTERPRISE_AGENT_CONSTITUTION, "timestamp": 0.0}
            )
        with self._get_connection() as conn:
            sum_row = conn.execute(
                "SELECT summary, compacted_turns_count, updated_at FROM session_summaries WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if sum_row and sum_row["summary"]:
                history.append(
                    {
                        "role": "system",
                        "content": f"[Compacted Session Memory ({sum_row['compacted_turns_count']} earlier turns)]: {sum_row['summary']}",
                        "timestamp": sum_row["updated_at"],
                    }
                )
            cursor = conn.execute(
                "SELECT role, content, timestamp, tokens_estimated FROM conversation_history WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
                (session_id, limit),
            )
            for row in cursor.fetchall():
                history.append(dict(row))
        return history

    def get_template(self, tier_key: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM proposal_templates WHERE tier_key = ?",
                (tier_key,),
            ).fetchone()
            if row:
                return json.loads(row["payload_json"])
        return None

    def save_deal_proposal(self, record: Dict[str, Any]) -> str:
        proposal_id = record.get("proposal_id") or f"PROP-{uuid.uuid4().hex[:8].upper()}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO deal_proposals (
                    proposal_id, session_id, customer_name, opportunity_name,
                    qualification_score, qualification_status, recommended_tier,
                    net_price_usd, hitl_status, proposal_markdown, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    record.get("session_id", "default"),
                    record.get("customer_name", "Enterprise Client"),
                    record.get("opportunity_name", "AI Transformation"),
                    int(record.get("qualification_score", 0)),
                    record.get("qualification_status", "UNKNOWN"),
                    record.get("recommended_tier", "tier_1_discovery_sprint"),
                    float(record.get("net_price_usd", 0.0)),
                    record.get("hitl_status", "AUTO_APPROVED"),
                    record.get("proposal_markdown", ""),
                    json.dumps(record),
                    time.time(),
                ),
            )
            conn.commit()
        return proposal_id

    def get_recent_proposals(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT proposal_id, session_id, customer_name, opportunity_name,
                       qualification_score, qualification_status, recommended_tier,
                       net_price_usd, hitl_status, proposal_markdown, details_json, created_at
                FROM deal_proposals ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )
            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["details"] = json.loads(item.pop("details_json", "{}"))
                items.append(item)
            return items


global_memory_store = AgentMemoryStore()
