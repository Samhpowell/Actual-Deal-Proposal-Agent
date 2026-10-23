# Enterprise Deal Qualification & Proposal Drafting Agent

A Multi-Agent AI assistant built with the **Google Agent Development Kit (ADK)** and **Gemini 2.5** that checks enterprise deal qualification criteria and drafts a Statement of Work (SOW) proposal from standardized templates.

---

## 1. Problem & Solution

- **Problem**: Account teams spend significant manual effort checking incoming enterprise opportunities against qualification checklists, estimating delivery pod staffing, and putting together initial Statement of Work (SOW) proposals.
- **Solution**: This agent uses a Coordinator + Sequential Multi-Agent workflow in Google ADK to:
  1. Check deal qualification criteria across five areas (business value metrics, executive sponsor, technical readiness, confirmed budget, and timeline).
  2. Calculate delivery pod staffing and commercial pricing based on the recommended sprint tier.
  3. Pull the matching SOW template from SQLite storage and generate a customized draft proposal.
  4. Pause for Human-in-the-Loop (HITL) approval when a deal is $500k+ or requests a discount over 15%.

---

## 2. Architecture

- `EnterpriseDealCoordinatorAgent` (Root Coordinator)
  - `DealQualificationSpecialistAgent` (`gemini-2.5-flash`): Scores opportunity qualification criteria (`evaluate_deal_qualification_criteria`).
  - `ResourceSizingSpecialistAgent` (`gemini-2.5-flash`): Calculates sprint pod roles, hours, and pricing (`calculate_delivery_resource_estimate`).
  - `ProposalDraftingSpecialistAgent` (`gemini-2.5-pro`): Retrieves the template (`retrieve_proposal_template_by_tier`) and drafts the SOW proposal (`generate_structured_proposal_draft`).

---

## 3. Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Web UI or CLI
```bash
# Start the local web interface on http://localhost:8080
python3 app.py

# Or run from the command line
python3 cli.py
```

### 3. Run Unit Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
