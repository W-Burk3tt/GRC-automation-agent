import sqlite3
import sys
import os

# Reuse the logic already built and tested in the other scripts
from crosswalk import load_controls, find_candidates, ask_llm_for_mapping, save_crosswalk, normalize_pcidss_id
from draft_poam import get_control, draft_poam_entry, save_poam

DB_PATH = "data/grc.db"

def log_action(conn, action, source_control_id, details):
    import json
    conn.execute(
        "INSERT INTO audit_log (action, source_control_id, details) VALUES (?, ?, ?)",
        (action, source_control_id, json.dumps(details))
    )
    conn.commit()

def cmd_lookup(conn, args):
    if not args:
        print("Usage: lookup <control_id>")
        return
    control_id = args[0]
    cur = conn.execute(
        "SELECT framework, control_id, title, text, source_page FROM controls WHERE control_id = ?",
        (control_id,)
    )
    row = cur.fetchone()
    if not row:
        print(f"Control '{control_id}' not found.")
        return
    framework, cid, title, text, page = row
    print(f"\n[{framework}] {cid}" + (f" — {title}" if title else ""))
    print(f"Source page: {page}")
    print(f"\n{text[:800]}")
    log_action(conn, "lookup", control_id, {})

def cmd_crosswalk(conn, args):
    if not args:
        print("Usage: crosswalk <cmmc_control_id>")
        return
    control_id = args[0]

    cur = conn.execute(
        "SELECT control_id, title, text FROM controls WHERE control_id = ? AND framework = 'CMMC'",
        (control_id,)
    )
    row = cur.fetchone()
    if not row:
        print(f"CMMC control '{control_id}' not found.")
        return
    cmmc_control = {"control_id": row[0], "title": row[1], "text": row[2]}

    # Check if we already have mappings cached

    refresh = "--refresh" in args
    if refresh:
        args = [a for a in args if a != "--refresh"]

    existing = conn.execute(
        "SELECT pcidss_control_id, confidence, mapping_rationale FROM crosswalk WHERE cmmc_control_id = ?",
        (control_id,)
    ).fetchall()
    if existing and not refresh:
        print(f"\nExisting crosswalk mappings for {control_id} (from database):")
        for pid, conf, rationale in existing:
            print(f"  -> PCI-DSS {pid} ({conf}): {rationale[:100]}")
        print("\n(Run with --refresh to re-query the LLM instead of using cached results.)")
        return

    elif refresh:
        print(f"Refreshing crosswalk for {control_id} (clearing cached results)...")

    pcidss_controls = load_controls(conn, "PCI-DSS")
    candidates = find_candidates([cmmc_control], pcidss_controls)
    result = ask_llm_for_mapping(cmmc_control, candidates[control_id])

    log_action(conn, "crosswalk_attempt", control_id, {
        "candidates_considered": [c["control_id"] for c in candidates[control_id]],
        "result": result
    })

    mappings = result.get("mappings", [])
    if not mappings:
        print(f"No PCI-DSS mapping found for {control_id}.")
        return

    if refresh:
        conn.execute("DELETE FROM crosswalk WHERE cmmc_control_id = ?", (control_id,))
        conn.commit()

    for mapping in mappings:
        save_crosswalk(conn, control_id, mapping)
        print(f"  -> PCI-DSS {normalize_pcidss_id(mapping['pcidss_id'])} ({mapping['confidence']}): {mapping['rationale']}")
    print("\n[All mappings flagged requires_human_review — not auto-finalized]")

def cmd_poam(conn, args):
    if len(args) < 2:
        print('Usage: poam <control_id> "<gap description>"')
        return
    control_id = args[0]
    gap_description = " ".join(args[1:])

    control = get_control(conn, control_id)
    if not control:
        print(f"Control '{control_id}' not found.")
        return

    print(f"Drafting POA&M for {control['framework']} {control_id}...")
    draft = draft_poam_entry(control, gap_description)

    log_action(conn, "poam_draft", control_id, {"gap_description": gap_description, "draft": draft})

    if "error" in draft:
        print("Failed to generate draft:", draft.get("error"))
        return

    save_poam(conn, control_id, gap_description, draft)
    print(f"\nRemediation plan: {draft['remediation_plan']}")
    print(f"Suggested timeline: {draft['suggested_timeline']}")
    print(f"Risk if unaddressed: {draft['risk_if_unaddressed']}")
    print("\n[Status: draft_pending_review — requires human review before finalizing]")

def cmd_history(conn, args):
    if not args:
        print("Usage: history <control_id>")
        return
    control_id = args[0]
    cur = conn.execute(
        "SELECT action, timestamp, details FROM audit_log WHERE source_control_id = ? ORDER BY id",
        (control_id,)
    )
    rows = cur.fetchall()
    if not rows:
        print(f"No audit history for '{control_id}'.")
        return
    print(f"\nAudit history for {control_id}:")
    for action, timestamp, details in rows:
        print(f"  [{timestamp}] {action}")

def print_help():
    print("""
Available commands:
  lookup <control_id>              Show full control text
  crosswalk <cmmc_control_id>      Find/show PCI-DSS mappings for a CMMC control
  poam <control_id> "<gap>"        Draft a POA&M entry for an identified gap
  history <control_id>             Show audit log history for a control
  help                             Show this message
  exit                             Quit
""")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run build_db.py first.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    print("GRC Automation Agent (CMMC 2.0 Level 2 / PCI-DSS v4.0.1)")
    print("Type 'help' for commands, 'exit' to quit.\n")

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()

        # Handle quoted args properly (for poam's gap description)
        import shlex
        try:
            args = shlex.split(raw)[1:]
        except ValueError:
            args = raw.split()[1:]

        if cmd == "exit" or cmd == "quit":
            print("Exiting.")
            break
        elif cmd == "help":
            print_help()
        elif cmd == "lookup":
            cmd_lookup(conn, args)
        elif cmd == "crosswalk":
            cmd_crosswalk(conn, args)
        elif cmd == "poam":
            cmd_poam(conn, args)
        elif cmd == "history":
            cmd_history(conn, args)
        else:
            print(f"Unknown command: '{cmd}'. Type 'help' for options.")

    conn.close()

if __name__ == "__main__":
    main()
