
import json
import re

from modules.llm_provider import generate_response

def extract_document_data(document_text: str, filename: str = "") -> dict:
    """
    Extract structured vendor information from document text
    using Gemini with Cloudflare fallback.
    """

    if not document_text or not document_text.strip():
        return {
            "success": False,
            "error": "No readable text found in document.",
            "filename": filename
        }

    
    prompt = f"""
You are an expert document classification and information extraction
assistant for a vendor onboarding system.

Your task is to analyze ONE PDF PAGE at a time.

DOCUMENT FILENAME:
{filename}

DOCUMENT TEXT:
{document_text[:15000]}

Return ONLY valid JSON. Do not include Markdown or explanations.

Use exactly this JSON structure:

{{
    "company_name": null,
    "person_name": null,
    "document_type": "UNKNOWN",
    "pan": null,
    "gstin": null,
    "account_holder_name": null,
    "bank_name": null,
    "account_number": null,
    "ifsc": null,
    "address": null,
    "extraction_status": "SUCCESS",
    "missing_fields": []
}}

CLASSIFICATION RULES:

1. Classify the current page independently.
2. Use only these document_type values:
   PAN, GST, BANK, UNKNOWN.

3. PAN:
   Identify as PAN only when the page contains clear evidence
   of a PAN card or PAN document.

4. GST:
   Identify as GST only when the page contains clear evidence
   of a GST registration certificate or GST document.

5. BANK:
   Identify as BANK only when the page contains clear evidence
   of a bank statement, cancelled cheque, passbook, or bank
   account proof.

6. UNKNOWN:
   Use UNKNOWN for unrelated pages, unclear documents,
   and pages without sufficient evidence.

7. Do not classify a page as PAN, GST, or BANK merely because
   it contains a PAN number, GSTIN, or bank account number.
   Consider the document's actual purpose and content.

EXTRACTION RULES:

8. Extract only information explicitly present on this page.
9. Use null when a field is unavailable.
10. Never invent or infer missing values.
11. Preserve PAN, GSTIN, IFSC, and account numbers exactly.
12. Do not extract a person's name from a company name.
13. person_name should contain an actual individual person's
    name only. If none is present, return null.
14. extraction_status:
    SUCCESS = useful information extracted.
    PARTIAL = some information extracted but incomplete.
    FAILED = no useful information extracted.
15. List unavailable relevant fields in missing_fields.

Return JSON only.
"""



    try:
        response = generate_response(prompt)

        if not response or not response.get("success"):
            return {
                "success": False,
                "filename": filename,
                "error": "All configured LLM providers failed.",
                "provider_errors": response.get("errors", []) if response else []
            }

        model_text = response.get("text", "")

        # Remove Markdown code fences if the model adds them.
        model_text = model_text.strip()
        model_text = re.sub(r"^```(?:json)?\s*", "", model_text)
        model_text = re.sub(r"\s*```$", "", model_text)

        # Parse model response into Python dictionary.
        extracted_data = json.loads(model_text)

        if not isinstance(extracted_data, dict):
            raise ValueError("LLM response is not a JSON object.")

        return {
            "success": True,
            "filename": filename,
            "data": extracted_data,
            "provider": response.get("provider"),
            "model": response.get("model"),
            "fallback": response.get("fallback_used", False)
        }

    except json.JSONDecodeError as error:
        return {
            "success": False,
            "filename": filename,
            "error": f"Invalid JSON returned by LLM: {error}"
        }

    except Exception as error:
        return {
            "success": False,
            "filename": filename,
            "error": str(error)
        }