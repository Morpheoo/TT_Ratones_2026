import pypdf
import sys

def extract_pdf_text(pdf_path, txt_path):
    try:
        reader = pypdf.PdfReader(pdf_path)
        with open(txt_path, 'w', encoding='utf-8') as f:
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    f.write(text + "\n")
        print(f"Successfully extracted text to {txt_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        extract_pdf_text(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python read_pdf.py <in.pdf> <out.txt>")
