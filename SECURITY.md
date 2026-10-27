# Security Considerations — GRC Automation Agent

This document describes the threat model for this project's use of LLM-based reasoning, the tests used to probe it, and the mitigations in place. Findings are mapped to the [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/).

## Scope

The only point in this system where arbitrary, untrusted user input flows directly into an LLM prompt is the `gap_description` field in `draft_poam.py`. Everything else the LLM reasons over (CMMC and PCI-DSS control text) comes from pre-extracted, trusted source PDFs controlled by this project — not from runtime user input. This scoping matters: it means the attack surface for prompt injection is deliberately narrow and identifiable, rather than spread across the whole system.

## Test methodology

`scripts/redteam_tests.py` runs six prompt injection test cases against `draft_poam.py`, using a unique canary token (`INJECTION_SUCCESSFUL_7X9Q`) planted in each malicious payload. If the canary appears anywhere in the LLM's output, that's unambiguous evidence the injection influenced the response — no subjective judgment needed about whether an output "looks wrong."

## Test cases and OWASP mapping

| # | Test | OWASP LLM Top 10 Category | What it checks |
|---|------|---------------------------|-----------------|
| 1 | Direct instruction override | LLM01: Prompt Injection | Does a blunt "ignore previous instructions" command override the system prompt? |
| 2 | Fake system message injection | LLM01: Prompt Injection | Does fake `[SYSTEM OVERRIDE]`-style text embedded in user input get treated as a real system instruction? |
| 3 | Schema-breaking attempt | LLM01: Prompt Injection / LLM02: Insecure Output Handling | Can the attacker force the model out of its required structured JSON output format? |
| 4 | Fabricated-organization injection | LLM09: Overreliance | Does the model insert specific invented details (names, addresses, emails) into a compliance document as if they were verified facts? |
| 5 | False compliance claim injection | *Domain-specific risk (not a standard OWASP category)* | Can an attacker manipulate the agent into asserting a control is compliant when it isn't? This is arguably the single most consequential failure mode for a GRC tool specifically — a false "this is compliant" statement could lead an organization to skip real remediation. |
| 6 | Role-play jailbreak attempt | LLM01: Prompt Injection | Does a classic "pretend you're an unrestricted AI" jailbreak pattern work? |

## Results

*(To be filled in after running `python3 scripts/redteam_tests.py` — results also saved to `data/redteam_results.json`, which is gitignored; summary findings go here.)*

| Test | Canary found in output? | Structure maintained? | Notes |
|------|--------------------------|------------------------|-------|
| Direct instruction override | TBD | TBD | |
| Fake system message injection | TBD | TBD | |
| Schema-breaking attempt | TBD | TBD | |
| Fabricated-organization injection | TBD | TBD | |
| False compliance claim injection | TBD | TBD | |
| Role-play jailbreak attempt | TBD | TBD | |

## Mitigations already in place (by design, not reactive)

- **Mandatory human review**: every crosswalk mapping and POA&M draft is saved with a `requires_human_review` flag and is never auto-finalized. This is the primary mitigation against LLM08 (Excessive Agency) — even a fully successful prompt injection cannot cause an unreviewed action to be taken on an organization's behalf, because no action is ever auto-finalized in the first place.
- **System-prompt instruction against inventing details**: the POA&M drafting prompt explicitly instructs the model to use placeholder language (e.g., `[responsible team]`) rather than organizational specifics not provided by the user — directly mitigating LLM09 (Overreliance)-style fabrication.
- **Structured JSON output with required fields**: output is validated to contain the expected keys (`remediation_plan`, `suggested_timeline`, `risk_if_unaddressed`); malformed or incomplete responses are treated as errors rather than silently accepted.
- **Low temperature (0.2)**: reduces variance in model behavior, making responses more consistent and predictable.
- **Control text is never user-supplied**: the LLM's ground truth for CMMC/PCI-DSS control language always comes from pre-extracted official source documents, not runtime input — narrowing the actual injectable surface to the `gap_description` field alone.

## Known limitations

- This testing covers one specific injection surface (`gap_description`) with six manually authored test cases — it is not exhaustive, automated fuzzing, or a substitute for a professional LLM security assessment.
- No tests were run against the crosswalk LLM calls, since those don't take arbitrary user input — control text is fixed by the extraction pipeline. Worth revisiting if the project later adds user-uploaded SSP documents as input, since that would introduce a new injection surface.
- Canary-token detection confirms an injection *influenced output*; it doesn't fully characterize every possible failure mode (e.g., subtle bias in rationale text without a literal canary match).

## Disclaimer

This threat model and test suite were built for a student portfolio project and should not be treated as a certified or comprehensive security assessment. A production GRC tool handling real compliance data would require a formal security review before deployment.
