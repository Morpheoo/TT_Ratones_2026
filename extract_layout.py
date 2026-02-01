from pypdf import PdfReader

reader = PdfReader("TT_2026-A155.pdf")
# Extract pages around 67 (index 66)
start_page = 65
end_page = 75

with open("requirements_layout.txt", "w", encoding="utf-8") as f:
    for i in range(start_page, end_page):
        try:
            page = reader.pages[i]
            text = page.extract_text(extraction_mode="layout")
            f.write(f"--- Page {i+1} ---\n")
            f.write(text + "\n")
        except Exception as e:
            f.write(f"\nError extracting page {i+1}: {e}\n")

print("Layout extraction complete.")
