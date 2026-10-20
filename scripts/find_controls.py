import pdfplumber
import re
import sys
from collections import defaultdict

# Wider title capture: letters, numbers, spaces, and common punctuation in titles
CONTROL_PATTERN = re.compile(r'([A-Z]{2}\.L2-3\.\d+\.\d+)\s*[–-]\s*([A-Za-z0-9 ,\[\]&/\']+?)(?=\s{2,}|\.{3,}|\n|$)')

def find_controls(path):
    occurrences = defaultdict(list)
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            matches = CONTROL_PATTERN.findall(text)
            for control_id, title in matches:
                occurrences[control_id.strip()].append((title.strip(), i + 1))
    return occurrences

if __name__ == "__main__":
    path = sys.argv[1]
    occurrences = find_controls(path)
    print(f"Found {len(occurrences)} unique control IDs\n")

    # Show the first 10 controls and ALL the pages each one appears on
    for control_id in list(occurrences.keys())[:10]:
        pages_and_titles = occurrences[control_id]
        print(f"{control_id}:")
        for title, page in pages_and_titles:
            print(f"   page {page}: \"{title}\"")
        print()
