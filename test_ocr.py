
from modules.document_processor import extract_pdf_text

pdf_path = r"C:\Users\91626\vendorflow_ai\vendorflow_ai_starter\vendorflow_ai\Scanned_Image_Only_OCR_Required.pdf"

result = extract_pdf_text(pdf_path)

print("Success:", result["success"])
print("Total Pages:", result["pages"])
print("OCR Used:", result["ocr_used"])

for page in result["page_results"]:

    print("\n-------------------------")
    print("Page:", page["page_number"])
    print("OCR:", page["ocr_used"])
    print("Text:")
    print(page["text"][:1000])
