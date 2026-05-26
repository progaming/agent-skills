---
name: progaming-applicant-scorer
description: "Fetch job application emails sent to hr@progaming.co.th from Gmail (which are auto-forwarded to the user's own mailbox), parse attached PDF resumes, extract candidate information (name, university, field of study, expected salary, skills), score against ProGaming job descriptions, and output ranked CSV/markdown tables. Use when the user asks to: (1) check or fetch job applicants from Gmail, (2) score or rank candidates applying to ProGaming, (3) evaluate resumes for Fullstack Developer or System Analyst positions, (4) generate applicant summary reports from hr@progaming.co.th emails."
---

# ProGaming Applicant Scorer

## Overview

This skill automates fetching job applications sent to `hr@progaming.co.th` from Gmail (which are auto-forwarded to the user's own mailbox), parsing attached PDF resumes, extracting candidate details, scoring them against ProGaming's job descriptions, and producing ranked summary tables (Markdown + CSV).

**Important:** The `hr@progaming.co.th` address is configured to auto-forward to the user's mailbox. Therefore, the application emails appear in the user's inbox with `hr@progaming.co.th` in the `To` field. Search the user's own inbox using `to:hr@progaming.co.th`, not the `hr@` mailbox directly.

## Quick Start (One-Shot Runner)

The fastest way to get results is the `run.py` script, which fetches, scores, and outputs in one command:

```bash
cd .agents/skills/progaming-applicant-scorer/scripts
python run.py --after 2026/05/24
```

This will:
1. Search Gmail for emails to `hr@progaming.co.th` after the specified date
2. Download message payloads and PDF attachments to a dated workspace under `Cowork/tmp/`
3. Extract and score each applicant
4. Print a Markdown table and write a CSV

**Default behavior:** If `--after` is omitted, it searches for today's emails.

## Alternative: Manual Workflow

For inspecting intermediate data or debugging, use the multi-step approach:

1. Create a workspace directory (or let `score_applicants.py` auto-create one)
2. Discover emails with `gws` (see PowerShell-safe examples below)
3. Save full payloads and download attachments
4. Run `python score_applicants.py --workspace <DIR>`

### Step 1: Fetch Email IDs

```powershell
$after = "2026/05/24"
$params = '{"userId":"me","q":"in:inbox to:hr@progaming.co.th after:' + $after + '"}'
gws gmail users messages list --params $params --page-all --format json
```

**PowerShell JSON safety:** Always build JSON strings via concatenation (`'{"id":"' + $id + '"}'`) rather than inline interpolation inside double-quoted strings. PowerShell treats `{` as a format-token trigger in double-quoted strings, which silently corrupts JSON.

### Step 2: Download Messages & Attachments

```powershell
$msgId = "19e5b7be55a093ad"
$params = '{"userId":"me","id":"' + $msgId + '","format":"full"}'
gws gmail users messages get --params $params --format json
```

For each attachment:
```powershell
$attachId = "<attachmentId>"
$params = '{"userId":"me","messageId":"' + $msgId + '","id":"' + $attachId + '"}'
gws gmail users messages attachments get --params $params --format json
```

**Tip:** The gws output may have ANSI color codes and a keyring log line before the JSON. Strip those before parsing JSON.

### Step 3: Extract Information

Parse email body + PDF text (using pdfplumber) and extract:
- **Name** — from email `From` header or resume header
- **Position Applied** — Fullstack Developer or System Analyst (from subject/body)
- **University** — see `references/scoring-rubric.md` for tier list
- **Field of Study** — CS/SE/IT/etc. mapped to score
- **Expected Salary** — numeric value near salary keywords, validated ฿10k–100k
- **Employment Status** — only detect "Fresh Graduate"; everything else is "Unknown"
- **JD Fit** — keyword-match resume against position requirements

### Step 4: Score

4 criteria, each 1–5, total out of 20:

| Criterion | Scoring |
|-----------|---------|
| University | Tier 1 = 5, Tier 2 = 3, Tier 3 = 2, Unknown = 3 |
| Field | CS/SE/IT/CE = 5, IS/Data Science = 4, tangential = 2, Unknown = 3 |
| Salary | <฿25k = 5, <฿35k = 4, <฿45k = 3, <฿60k = 2, >=฿60k = 1, Not declared = 3 |
| JD Fit | Strong (6+ keywords) = 5, Good (4+) = 4, Moderate (2+) = 3, Weak (1) = 2, Unknown = 3 |

**Rules:**
- Unknown values get a middle score of 3 (not 0 or 1) so they don't underweight.
- Employment status is **informational only** — no score contribution. Only "Fresh Graduate" or "Unknown".
- Deduplicate by (name + position).

### Step 5: Output

Generate:
- Markdown table: Rank | Name | Position | University | Field | Salary | Status | Score (U/F/S/J) | Total | JD Fit | Note
- CSV with same columns + individual score columns

## Position Definitions

**Fullstack Developer** (from `hiring/jd-fullstack-ai-platform.md`):
- Frontend: React, TypeScript, HTML5/CSS3
- Backend: Node.js, RESTful API Design
- General: Web Application, Dashboard, Visualization, Interactive UI

**System Analyst** (from `hiring/js-system-analyst.md`):
- Analysis: Requirement gathering, business/system analysis
- Documentation: System Specification, Data Flow Diagram, Use Cases
- Technical Communication: RESTful APIs, Database, Web Application
- Trends: AI, Automation, Gamification

## References

- **University tiers, field mappings, salary bands**: See `references/scoring-rubric.md`
- **JD keyword lists per position**: See `references/jd-keywords.md`

## Scripts

- **`scripts/run.py`**: One-shot runner. Fetches emails, downloads attachments, scores applicants, and outputs CSV + Markdown. Use `--after YYYY/MM/DD` to set the search date (defaults to today). Automatically creates a dated workspace under `Cowork/tmp/`.
- **`scripts/score_applicants.py`**: Standalone scoring pipeline for local data. Use `--workspace` to point at an existing directory. If omitted, auto-creates a dated directory under `Cowork/tmp/`.
