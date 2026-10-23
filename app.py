"""Interactive Web Application for Enterprise Deal Qualification & SOW Proposal Drafting."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from agent_app.hitl import global_hitl_controller
from agent_app.memory_store import global_memory_store
from agent_app.orchestrator import global_coordinator_agent

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Enterprise Deal Qualification & Proposal Agent</title>
  <style>
    :root {
      --bg: #f8fafc;
      --card: #ffffff;
      --primary: #1a73e8;
      --text: #0f172a;
      --muted: #475569;
      --border: #e2e8f0;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }
    .container { max-width: 1180px; margin: 0 auto; }
    header {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    h1 { margin: 0 0 6px 0; font-size: 22px; }
    .subtitle { color: var(--muted); font-size: 14px; margin: 0; }
    .badge {
      background: #e0f2fe;
      color: #0369a1;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
    }
    .grid { display: grid; grid-template-columns: 400px 1fr; gap: 20px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
    }
    .card h2 { margin-top: 0; font-size: 17px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
    label { display: block; font-size: 13px; font-weight: 600; margin-top: 12px; margin-bottom: 4px; }
    input[type="text"], input[type="number"], select, textarea {
      width: 100%;
      box-sizing: border-box;
      padding: 9px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 14px;
    }
    textarea { height: 76px; resize: vertical; }
    .checkbox-row { display: flex; gap: 16px; margin-top: 12px; }
    .checkbox-row label { display: flex; align-items: center; gap: 6px; font-weight: 500; margin: 0; }
    button {
      margin-top: 18px;
      width: 100%;
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 12px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
    }
    button:hover { background: #1557b0; }
    .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
    .kpi {
      background: #f1f5f9;
      padding: 12px;
      border-radius: 8px;
    }
    .kpi .label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
    .kpi .val { font-size: 18px; font-weight: 700; margin-top: 4px; }
    pre {
      background: #0f172a;
      color: #f8fafc;
      padding: 16px;
      border-radius: 8px;
      white-space: pre-wrap;
      font-size: 13px;
      line-height: 1.5;
      max-height: 520px;
      overflow-y: auto;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Enterprise Deal Qualification & Proposal Drafting Agent</h1>
        <p class="subtitle">Google ADK Multi-Agent Coordinator: Qualification Triage &rarr; Pod Sizing &rarr; Template SOW Authoring</p>
      </div>
      <span class="badge">ADK Multi-Agent</span>
    </header>

    <div class="grid">
      <div class="card">
        <h2>1. Opportunity Intake & Qualification</h2>
        <label>Customer Name</label>
        <input type="text" id="customer_name" value="Acme Global Manufacturing" />

        <label>Opportunity Title</label>
        <input type="text" id="opportunity_name" value="Supply Chain AI Triage & Predictive Operations" />

        <label>Estimated Deal Value (USD)</label>
        <input type="number" id="estimated_deal_value_usd" value="350000" />

        <div class="checkbox-row">
          <label><input type="checkbox" id="executive_sponsor_identified" checked /> Executive Sponsor</label>
          <label><input type="checkbox" id="budget_confirmed" checked /> Budget Confirmed</label>
        </div>

        <label>Quantified Business Value & Problem Summary</label>
        <textarea id="quantified_business_metrics">Reduce manual supply chain exception triage by 45% and save $1.4M annually across 3 regional hubs.</textarea>

        <label>Technical & Data Readiness</label>
        <select id="technical_readiness_level">
          <option value="HIGH" selected>HIGH - Cloud & Data Ready</option>
          <option value="MEDIUM">MEDIUM - Partial Cloud Footprint</option>
          <option value="LOW">LOW - Legacy On-Premises</option>
        </select>

        <label>Target Timeline (Weeks)</label>
        <input type="number" id="target_timeline_weeks" value="8" />

        <label>Requested Discount (%)</label>
        <input type="number" id="requested_discount_pct" value="5" />

        <button onclick="runEvaluation()">Check Qualification & Build Draft Proposal</button>
      </div>

      <div class="card">
        <h2>2. Qualification Scorecard & Generated SOW Draft</h2>
        <div class="kpi-row">
          <div class="kpi">
            <div class="label">Qualification Score</div>
            <div class="val" id="kpi_score">-- / 100</div>
          </div>
          <div class="kpi">
            <div class="label">Status</div>
            <div class="val" id="kpi_status" style="font-size:13px;">Ready</div>
          </div>
          <div class="kpi">
            <div class="label">Net Investment</div>
            <div class="val" id="kpi_price">--</div>
          </div>
          <div class="kpi">
            <div class="label">HITL Governance</div>
            <div class="val" id="kpi_hitl" style="font-size:13px;">--</div>
          </div>
        </div>
        <pre id="proposal_output">Click "Check Qualification & Build Draft Proposal" to run the multi-agent pipeline...</pre>
      </div>
    </div>
  </div>

  <script>
    async function runEvaluation() {
      const out = document.getElementById("proposal_output");
      out.textContent = "Running ADK Coordinator -> Qualification -> Sizing -> Proposal Drafting Sub-Agents...";
      const payload = {
        customer_name: document.getElementById("customer_name").value,
        opportunity_name: document.getElementById("opportunity_name").value,
        estimated_deal_value_usd: parseFloat(document.getElementById("estimated_deal_value_usd").value || "0"),
        executive_sponsor_identified: document.getElementById("executive_sponsor_identified").checked,
        budget_confirmed: document.getElementById("budget_confirmed").checked,
        quantified_business_metrics: document.getElementById("quantified_business_metrics").value,
        business_problem_summary: document.getElementById("quantified_business_metrics").value,
        technical_readiness_level: document.getElementById("technical_readiness_level").value,
        target_timeline_weeks: parseInt(document.getElementById("target_timeline_weeks").value || "8", 10),
        requested_discount_pct: parseFloat(document.getElementById("requested_discount_pct").value || "0")
      };

      const resp = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (data.status !== "SUCCESS") {
        out.textContent = "Guardrail / Validation Alert: " + (data.message || JSON.stringify(data, null, 2));
        return;
      }
      document.getElementById("kpi_score").textContent = data.qualification.qualification_score + " / 100";
      document.getElementById("kpi_status").textContent = data.qualification.qualification_status;
      document.getElementById("kpi_price").textContent = "$" + data.resource_estimate.net_price_usd.toLocaleString();
      document.getElementById("kpi_hitl").textContent = data.hitl_governance.hitl_status;
      out.textContent = data.proposal.proposal_markdown;
    }
  </script>
</body>
</html>
"""


class DealAgentHTTPRequestHandler(BaseHTTPRequestHandler):
    """Serves the interactive Web UI and JSON REST endpoints."""

    def _send_json(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path in ["/", "/index.html"]:
            raw = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/history":
            self._send_json(
                {
                    "pending_hitl": global_hitl_controller.list_pending(),
                    "recent_proposals": global_memory_store.get_recent_proposals(limit=10),
                }
            )
        else:
            self._send_json({"error": "Not found"}, status_code=404)

    def do_POST(self) -> None:
        if self.path == "/api/evaluate":
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            payload = json.loads(body or "{}")
            result = global_coordinator_agent.evaluate_and_draft_proposal(payload)
            self._send_json(result)
        else:
            self._send_json({"error": "Not found"}, status_code=404)

    def log_message(self, format_str: str, *args: Any) -> None:
        return


def run_server(port: int = 8080) -> None:
    server = HTTPServer(("0.0.0.0", port), DealAgentHTTPRequestHandler)
    print(f"Enterprise Deal Qualification & Proposal Agent UI running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port_num = int(os.environ.get("PORT", "8080"))
    run_server(port=port_num)
