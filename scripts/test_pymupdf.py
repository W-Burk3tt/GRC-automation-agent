import fitz  # PyMuPDF
import sys

def inspect(path, page_num):
    doc = fitz.open(path)
    page = doc[page_num - 1]  # 0-indexed
    text = page.get_text()
    print(text[:2000])

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    inspect(path, page_num)
