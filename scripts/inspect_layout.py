import pdfplumber
import sys
from collections import defaultdict

def inspect_layout(path, page_num):
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        print(f"Page width: {page.width}, height: {page.height}\n")

        # Group characters into lines by their 'top' position (rounded to nearest pixel)
        lines = defaultdict(list)
        for char in page.chars:
            lines[round(char['top'])].append(char)

        # Print each line's x-range and text, sorted top to bottom
        for top in sorted(lines.keys()):
            chars = sorted(lines[top], key=lambda c: c['x0'])
            text = "".join(c['text'] for c in chars)
            x_min = min(c['x0'] for c in chars)
            x_max = max(c['x1'] for c in chars)
            print(f"top={top:4} x=({x_min:.0f}-{x_max:.0f}): {text}")

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    inspect_layout(path, page_num)

