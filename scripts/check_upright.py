import pdfplumber
import sys

def inspect(path, page_num, top_target, tolerance=2):
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        chars = [c for c in page.chars if abs(c['top'] - top_target) <= tolerance]
        chars.sort(key=lambda c: c['x0'])
        for c in chars:
            print(f"text='{c['text']}' font={c['fontname']:25} upright={c.get('upright')} matrix={c.get('matrix')}")

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    top_target = float(sys.argv[3])
    inspect(path, page_num, top_target)
