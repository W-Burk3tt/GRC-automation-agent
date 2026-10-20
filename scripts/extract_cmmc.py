import fitz  # PyMuPDF
import re
import json
import sys
import os

CONTROL_PATTERN = re.compile(r'^([A-Z]{2}\.L2-3\.\d+\.\d+)\s*[–-]\s*(.+)$', re.MULTILINE)

NOISE_PATTERNS = [
    re.compile(r'^CMMC Assessment Guide.*Version \d+\.\d+.*$'),
    re.compile(r'^\s*\d{1,3}\s*$'),  # standalone page numbers
]

def extract_all_text(path):
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append((i + 1, text))
    return pages

def clean_text(text):
    lines = text.split('\n')
    cleaned = [line for line in lines if not any(p.match(line.strip()) for p in NOISE_PATTERNS)]
    return "\n".join(cleaned)

def find_body_starts(pages, toc_cutoff_page=15):
    first_body_page = {}
    first_body_title = {}
    for page_num, text in pages:
        if page_num <= toc_cutoff_page:
            continue
        for line in text.split('\n'):
            match = CONTROL_PATTERN.match(line.strip())
            if match:
                control_id = match.group(1).strip()
                title = match.group(2).strip()
                if control_id not in first_body_page:
                    first_body_page[control_id] = page_num
                    first_body_title[control_id] = title
    return first_body_page, first_body_title

def build_control_ranges(first_body_page):
    ordered = sorted(first_body_page.items(), key=lambda x: x[1])
    ranges = []
    for idx, (control_id, start_page) in enumerate(ordered):
        if idx + 1 < len(ordered):
            end_page = ordered[idx + 1][1]
        else:
            end_page = start_page + 3
        ranges.append((control_id, start_page, end_page))
    return ranges

def extract_control_text(pages, start_page, end_page):
    page_dict = dict(pages)
    full_text = []
    for p in range(start_page, end_page + 1):
        if p in page_dict:
            full_text.append(page_dict[p])
    return "\n".join(full_text)

if __name__ == "__main__":
    path = sys.argv[1]
    pages = extract_all_text(path)
    first_body_page, first_body_title = find_body_starts(pages)
    ranges = build_control_ranges(first_body_page)

    print(f"Total controls found: {len(ranges)}\n")

    controls = []
    for control_id, start_page, end_page in ranges:
        raw_text = extract_control_text(pages, start_page, end_page)
        text = clean_text(raw_text)
        controls.append({
            "control_id": control_id,
            "title": first_body_title[control_id],
            "start_page": start_page,
            "end_page": end_page,
            "text": text
        })

    os.makedirs("data", exist_ok=True)
    with open("data/cmmc_controls_raw.json", "w") as f:
        json.dump(controls, f, indent=2)

    print("Saved to data/cmmc_controls_raw.json")
    print("\nFirst 3 controls (ID, title, page range):")
    for c in controls[:3]:
        print(f"  {c['control_id']} | {c['title']} | pages {c['start_page']}-{c['end_page']}")

