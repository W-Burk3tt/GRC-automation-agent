import pdfplumber
import sys

def inspect(path, start_page=1, num_pages=3):
    with pdfplumber.open(path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        end_page = min(start_page + num_pages, len(pdf.pages) + 1)
        for i in range(start_page - 1, end_page - 1):
            page = pdf.pages[i]
            print(f"\n--- Page {i+1} ---")
            text = page.extract_text()
            if text:
                print(text[:1000])
            else:
                print("[No extractable text on this page]")

if __name__ == "__main__":
    path = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    num = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    inspect(path, start, num)
