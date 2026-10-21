import fitz
import re
import json
import sys
import os

# Matches requirement IDs like "1.1.1", "2.2.3", "12.10.1" at the start of a block
REQUIREMENT_PATTERN = re.compile(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+(.+)', re.DOTALL)

# Column x-ranges (tuned from page 44 inspection; may need slight adjustment per page)
COL1_X_RANGE = (60, 295)   # Defined Approach Requirements
COL2_X_RANGE = (295, 512)  # Defined Approach Testing Procedures

def classify_column(x0, x1):
    mid = (x0 + x1) / 2
    if COL1_X_RANGE[0] <= mid <= COL1_X_RANGE[1]:
        return "requirements"
    elif COL2_X_RANGE[0] <= mid <= COL2_X_RANGE[1]:
        return "testing"
    else:
        return "guidance"

def extract_page_columns(page):
    blocks = page.get_text("blocks")
    columns = {"requirements": [], "testing": [], "guidance": []}
    for b in blocks:
        x0, y0, x1, y1, text, block_no, block_type = b
        if not text.strip():
            continue
        col = classify_column(x0, x1)
        columns[col].append((y0, text.strip()))
    # Sort each column top-to-bottom
    for col in columns:
        columns[col].sort(key=lambda t: t[0])
    return columns

def extract_all_requirements(path, start_page=44, end_page=397):
    doc = fitz.open(path)
    requirements = {}  # requirement_id -> {text pieces}
    current_id = None

    for page_num in range(start_page - 1, min(end_page, len(doc))):
        page = doc[page_num]
        columns = extract_page_columns(page)
        req_blocks = [text for _, text in columns["requirements"]]

        for block_text in req_blocks:
            match = REQUIREMENT_PATTERN.match(block_text)
            if match:
                req_id = match.group(1)
                req_text = match.group(2)
                if req_id not in requirements:
                    requirements[req_id] = {
                        "requirement_id": req_id,
                        "text": req_text,
                        "page": page_num + 1
                    }
                else:
                    # Same ID seen again (e.g., sub-bullet continuation) — append
                    requirements[req_id]["text"] += " " + req_text
            elif current_id and block_text:
                # Continuation text (bullets, etc.) with no new ID at the start
                if current_id in requirements:
                    requirements[current_id]["text"] += " " + block_text
            if match:
                current_id = match.group(1)

    return requirements

def clean_requirement_text(text):
    # Trim at known section-boundary markers that signal we've bled into another column
    cutoff_markers = [
        "Customized Approach Objective",
        "Applicability Notes",
        "Defined Approach Testing Procedures",
    ]
    for marker in cutoff_markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    # Also trim if a new requirement ID (e.g., "1.2.1.b") appears mid-text — signals testing-procedure bleed
    text = re.sub(r'\s+\d{1,2}\.\d{1,2}\.\d{1,2}\.[a-z]\s+Examine.*$', '', text, flags=re.DOTALL)
    return text.strip()

if __name__ == "__main__":
    path = sys.argv[1]
    requirements = extract_all_requirements(path)

    for r in requirements.values():
        r["text"] = clean_requirement_text(r["text"])

    print(f"Total requirements found: {len(requirements)}\n")
    sample_ids = list(requirements.keys())[:5]
    for rid in sample_ids:
        r = requirements[rid]
        print(f"{rid} (page {r['page']}): {r['text'][:150]}")
        print()

    os.makedirs("data", exist_ok=True)
    with open("data/pcidss_requirements_raw.json", "w") as f:
        json.dump(list(requirements.values()), f, indent=2)
    print("Saved to data/pcidss_requirements_raw.json")
