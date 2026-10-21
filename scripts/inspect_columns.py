import fitz
import sys

def inspect(path, page_num):
    doc = fitz.open(path)
    page = doc[page_num - 1]
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
    print(f"Page width: {page.rect.width}\n")
    for b in blocks:
        x0, y0, x1, y1, text, block_no, block_type = b
        preview = text.strip().replace('\n', ' ')[:70]
        print(f"block {block_no}: x=({x0:.0f}-{x1:.0f}) y=({y0:.0f}-{y1:.0f}) | {preview}")

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    inspect(path, page_num)
