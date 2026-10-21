import fitz
import sys

def inspect(path, start_page, num_pages=3):
    doc = fitz.open(path)
    print(f"Total pages: {len(doc)}")
    for i in range(start_page - 1, min(start_page - 1 + num_pages, len(doc))):
        page = doc[i]
        print(f"\n--- Page {i+1} ---")
        text = page.get_text()
        print(text[:1200])

if __name__ == "__main__":
    path = sys.argv[1]
    start = int(sys.argv[2])
    num = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    inspect(path, start, num)
