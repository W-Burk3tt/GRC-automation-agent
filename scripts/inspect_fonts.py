import pdfplumber
import sys

def inspect_fonts(path, page_num, top_target, tolerance=2):
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[page_num - 1]
        print(f"Characters near top={top_target} (±{tolerance}):\n")
        for char in page.chars:
            if abs(char['top'] - top_target) <= tolerance:
                print(f"  text='{char['text']}' top={char['top']:.1f} font={char['fontname']} size={char['size']:.1f} color={char.get('non_stroking_color')}")

if __name__ == "__main__":
    path = sys.argv[1]
    page_num = int(sys.argv[2])
    top_target = float(sys.argv[3])
    inspect_fonts(path, page_num, top_target)
