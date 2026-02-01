from pypdf import PdfReader

reader = PdfReader("TT_2026-A155.pdf")
with open("requirements_dump.txt", "w", encoding="utf-8") as f:
    for page in reader.pages:
        try:
            text = page.extract_text()
            f.write(text + "\n")
        except Exception as e:
            f.write(f"\nError extracting page: {e}\n")

print("Extraction complete.")
