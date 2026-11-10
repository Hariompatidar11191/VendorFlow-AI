
import json
from modules.document_ai import extract_document_data

sample_text = """
INCOME TAX DEPARTMENT
Permanent Account Number

Name: ABC Technologies Private Limited
PAN: ABCDE1234F
"""

result = extract_document_data(
    document_text=sample_text,
    filename="sample_pan.pdf"
)

print("\n========== DOCUMENT AI TEST ==========")
print(json.dumps(result, indent=4))
print("======================================")