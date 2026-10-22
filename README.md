# GRC Automation Agent — CMMC 2.0 ↔ PCI-DSS v4.0.1

A text-based AI agent that automates GRC (Governance, Risk, Compliance) workflows: crosswalking controls between CMMC 2.0 Level 2 and PCI-DSS v4.0.1, and drafting POA&M (Plan of Action & Milestones) remediation entries — with every output flagged for mandatory human review.

Built as a portfolio project to apply cybersecurity/information assurance coursework to a real, in-demand problem space: agentic AI applied to compliance automation.

## What it does

- **`lookup <control_id>`** — retrieves full control text for any CMMC Level 2 practice or PCI-DSS v4.0.1 requirement
- **`crosswalk <cmmc_control_id>`** — identifies which PCI-DSS requirements address the same underlying security intent as a given CMMC practice, with a confidence rating (high/medium/low) and a cited rationale
- **`poam <control_id> "<gap description>"`** — drafts a remediation plan, suggested timeline, and risk statement for an identified compliance gap
- **`history <control_id>`** — shows the full audit trail of every agent action taken against a control

Every crosswalk mapping and POA&M draft is saved with a `requires_human_review` flag and is never auto-finalized — the agent assists a GRC analyst's judgment, it doesn't replace it.

## Architecture

- **Source data**: Official CMMC 2.0 Level 2 Assessment Guide (v2.13, DoD CIO) and PCI-DSS v4.0.1 Requirements and Testing Procedures (PCI Security Standards Council) — parsed directly from the authoritative PDFs, never relying on an LLM's memory of control text
- **Extraction**: PyMuPDF for PDF parsing (switched from `pdfplumber` after diagnosing a character-level text-interleaving issue in the CMMC PDF — see *Technical Challenges* below)
- **Storage**: SQLite — `controls`, `crosswalk`, `poam`, and `audit_log` tables
- **Candidate filtering**: TF-IDF + cosine similarity (scikit-learn) narrows ~27,000 possible CMMC×PCI-DSS pairs down to the top 5 candidates per CMMC control before any LLM call — keeping API cost and latency low
- **Reasoning**: OpenAI API (`gpt-4o-mini`), low temperature (0.2), structured JSON output, system-prompted to cite only the provided control text and never invent language
- **Interface**: Python CLI (`scripts/agent.py`)

## Why API-based reasoning, not a local model

Developed on an 8GB RAM Windows 11 laptop via WSL2. Running even a small local LLM alongside a dev environment wasn't viable on that hardware, so all reasoning happens via the OpenAI API — keeping the local footprint to just orchestration code and a lightweight SQLite database. This mirrors how GRC tooling is typically built in industry.

## Technical challenges and how they were solved

**PDF layout parsing (CMMC guide):** Initial extraction with `pdfplumber` produced garbled, character-interleaved text. Diagnosis at the character-coordinate level (position, font, color, transformation matrix) revealed the PDF embeds a margin annotation layer that `pdfplumber` incorrectly merges with body text during reading-order reconstruction. Resolved by switching to PyMuPDF (`fitz`), which parses the document's layout correctly.

**Multi-column table parsing (PCI-DSS guide):** PCI-DSS's "Requirements / Testing Procedures / Guidance" three-column table layout required coordinate-based column classification (not simple reading order) to avoid mixing requirement text with testing-procedure and guidance text. Solved with x-coordinate range filtering plus a content-based cleanup pass for edge cases where column boundaries shifted across pages.

**ID format consistency:** Early crosswalk runs showed the LLM occasionally echoing a "PCI-DSS" prefix into its JSON output for requirement IDs, breaking joins against the controls table. Fixed at both the prompt level (explicit formatting instruction) and the code level (defensive normalization on save) — a reminder that LLM output format can't be fully guaranteed by prompting alone.

## Guardrails

- Every crosswalk and POA&M output is saved with a human-review flag; nothing is auto-finalized
- The LLM is explicitly instructed to return an empty result rather than force a weak match — confirmed in testing, where ~28% of CMMC controls correctly returned no PCI-DSS mapping (reflecting that CMMC's CUI-protection scope is broader than PCI-DSS's cardholder-data scope)
- POA&M drafts use placeholder language (`[responsible team]`, `[organization]`) rather than inventing organizational details not provided by the user
- Every agent action (lookup, crosswalk attempt, POA&M draft) is written to an `audit_log` table with a timestamp
- `.env` (API key) is git-ignored and never committed; a spending cap is set on the OpenAI account

## Known limitations

- Crosswalk candidate pre-filtering (TF-IDF) is a shortlist, not exhaustive — a true match outside the top 5 candidates per control would be missed. A production system would need a larger candidate pool or a different retrieval strategy.
- No support yet for ingesting a real System Security Plan (SSP) document — current testing uses synthetic/fictional gap descriptions entered manually.
- Single-user, local SQLite — not designed for concurrent multi-user access.

## Setup

```bash
# WSL2/Ubuntu, Python 3.11+
python3 -m venv venv
source venv/bin/activate
pip install openai python-dotenv pymupdf scikit-learn

# Add your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env

# Download source PDFs into data/raw/ (see Sources below), then:
python3 scripts/extract_cmmc.py data/raw/cmmc_l2_assessment_guide.pdf
python3 scripts/extract_pcidss.py data/raw/pcidss_v4_0_1.pdf
python3 scripts/build_db.py

# Run the agent
python3 scripts/agent.py
```

## Sources

- CMMC 2.0 Level 2 Assessment Guide v2.13: https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf
- PCI-DSS v4.0.1: https://www.pcisecuritystandards.org/document_library/

## Disclaimer

This tool is a portfolio/learning project and does not constitute a certified compliance assessment. CMMC certification requires an accredited C3PAO assessor; PCI-DSS compliance validation requires a Qualified Security Assessor (QSA) or appropriate self-assessment process. All outputs require human review by a qualified GRC professional before any organizational use.
