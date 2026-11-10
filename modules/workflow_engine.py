
import json
import re

from modules.document_processor import extract_documents
from modules.document_ai import extract_document_data
from modules.validation_engine import validate_vendor

from database.database import (
    get_run_context,
    add_execution_event,
    save_validation_results,
    update_run
)


def normalize_value(value):
    """Normalize identifiers before comparing them."""
    if value is None:
        return ""

    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def get_vendor_value(vendor, field):
    """Safely read a field from the vendor record."""
    try:
        return vendor.get(field)
    except AttributeError:
        try:
            return vendor[field]
        except (KeyError, IndexError, TypeError):
            return None


def compare_document_fields(vendor, ai_results):
    """
    Compare fields extracted from documents against
    the vendor-submitted form.
    """

    comparisons = {
        "PAN": ("pan", "PAN"),
        "GSTIN": ("gstin", "GSTIN"),
        "IFSC": ("ifsc", "IFSC"),
        "ACCOUNT_NUMBER": ("bank_account", "ACCOUNT_NUMBER")
    }

    results = []

    for item in ai_results:

        if not item.get("success"):
            continue

        extracted = item.get("data", {})
        document_type = str(
            extracted.get("document_type", "UNKNOWN")
        ).upper()

        for extracted_field, (vendor_field, label) in comparisons.items():

            # Avoid checking unrelated fields against this document.
            relevant_types = {
                "PAN": ["PAN"],
                "GSTIN": ["GST"],
                "IFSC": ["BANK"],
                "ACCOUNT_NUMBER": ["BANK"]
            }

            if document_type not in relevant_types[extracted_field]:
                continue

            document_value = extracted.get(
                extracted_field.lower()
                if extracted_field != "ACCOUNT_NUMBER"
                else "account_number"
            )

            vendor_value = get_vendor_value(vendor, vendor_field)

            if not document_value or not vendor_value:
                continue

            if normalize_value(document_value) == normalize_value(vendor_value):
                result = "PASS"
                details = (
                    f"{label} extracted from {item.get('filename')} "
                    "matches the submitted vendor form."
                )
            else:
                result = "FAIL"
                details = (
                    f"{label} mismatch: document value does not "
                    "match the vendor-submitted value."
                )

            results.append({
                "check_name": f"Document Form Match - {label}",
                "result": result,
                "details": details
            })

    return results


def process_vendor(run_id, precomputed_ai_results=None):

    try:
        vendor, documents = get_run_context(run_id)

        # Stage 1: Submission
        add_execution_event(
            run_id,
            "Submission",
            "Completed",
            "Vendor submission loaded from SQLite."
        )

        # Stage 2: PDF text extraction
        add_execution_event(
            run_id,
            "Document Processing",
            "Running",
            "Extracting text from uploaded PDF files."
        )

        extraction_results = extract_documents([
            doc["stored_path"] for doc in documents
        ])

        successful = [
            item for item in extraction_results
            if item["success"]
        ]

        failed = [
            item for item in extraction_results
            if not item["success"]
        ]

        needs_ocr = [
            item for item in successful
            if item.get("needs_ocr")
        ]

        add_execution_event(
            run_id,
            "Document Processing",
            "Completed" if not failed else "Warning",
            f"{len(successful)} extracted, "
            f"{len(failed)} failed, {len(needs_ocr)} require OCR."
        )


        # Stage 3: AI document extraction

        add_execution_event(
            run_id,
            "AI Document Extraction",
            "Running",
            "Using previously extracted AI results or processing documents with Gemini."
        )

        if precomputed_ai_results is not None:
            ai_results = precomputed_ai_results

        else:
            ai_results = []

            for item in successful:

                if item.get("needs_ocr"):
                    ai_results.append({
                        "success": False,
                        "filename": item.get("filename"),
                        "error": "OCR is required before AI extraction."
                    })
                    continue

                ai_result = extract_document_data(
                    document_text=item.get("text", ""),
                    filename=item.get("filename", "")
                )

                ai_results.append(ai_result)

        ai_successful = [
            item for item in ai_results
            if item.get("success")
        ]

        ai_failed = [
            item for item in ai_results
            if not item.get("success")
        ]

        for item in ai_results:

            if item.get("success"):

                data = item.get("data", {})

                event_details = {
                    "filename": item.get("filename"),
                    "document_type": data.get("document_type"),
                    "extraction_status": data.get("extraction_status"),
                    "provider": item.get("provider"),
                    "model": item.get("model"),
                    "fallback": item.get("fallback", False),
                    "extracted_fields": {
                        key: value
                        for key, value in data.items()
                        if value is not None
                    }
                }

                add_execution_event(
                    run_id,
                    "AI Extraction Result",
                    "Completed",
                    json.dumps(event_details)
                )

            else:
                add_execution_event(
                    run_id,
                    "AI Extraction Result",
                    "Warning",
                    f"{item.get('filename')}: {item.get('error')}"
                )

        add_execution_event(
            run_id,
            "AI Document Extraction",
            "Completed" if not ai_failed else "Warning",
            f"{len(ai_successful)} documents processed by AI, "
            f"{len(ai_failed)} AI extraction failures."
        )


        # Stage 4: Form and document comparison
        add_execution_event(
            run_id,
            "Document Form Comparison",
            "Running",
            "Comparing extracted identifiers against submitted vendor details."
        )

        comparison_results = compare_document_fields(
            vendor,
            ai_successful
        )

        add_execution_event(
            run_id,
            "Document Form Comparison",
            "Completed",
            f"{len(comparison_results)} document-form comparisons performed."
        )

        # Stage 5: Existing validation engine
        add_execution_event(
            run_id,
            "Validation",
            "Running",
            "Checking vendor fields and document requirements."
        )

        validation_results = validate_vendor(
            vendor, documents , ai_results= ai_results
        )

        # Include document-to-form mismatches in final validation.
        validation_results.extend(comparison_results)

        # Mandatory Contact Person check
        contact_name = get_vendor_value(vendor, "contact_name")

        if not contact_name or not str(contact_name).strip():
            validation_results.append({
                "check_name": "Contact Person",
                "result": "MISSING",
                "details": (
                    "Contact Person is mandatory but was not provided "
                    "or extracted. Manual review is required."
                )
            })
        else:
            validation_results.append({
                "check_name": "Contact Person",
                "result": "PASS",
                "details": "Mandatory Contact Person field is available."
            })

        save_validation_results(
            run_id, validation_results
        )

        add_execution_event(
            run_id,
            "Validation",
            "Completed",
            f"{len(validation_results)} validation checks recorded."
        )

        # Stage 6: Preliminary decision
        failures = [
            r for r in validation_results
            if r["result"] == "FAIL"
        ]

        missing = [
            r for r in validation_results
            if r["result"] == "MISSING"
        ]

        reasons = []

        if failures:
            status = "Rejected"
            reasons = [r["details"] for r in failures]

        elif missing:
            status = "Pending"
            reasons = [r["details"] for r in missing]

        elif failed or needs_ocr or ai_failed:
            status = "Pending"
            reasons = [
                "Some documents could not be fully processed. "
                "Manual review required."
            ]

        else:
            status = "Approved"
            reasons = [
                "All implemented preliminary checks passed. "
                "External identity, GST and bank verification "
                "remain outstanding."
            ]

        reason = "; ".join(reasons)

        update_run(run_id, status, reason)

        add_execution_event(
            run_id,
            "Decision",
            "Completed",
            f"Preliminary decision: {status}. {reason}"
        )

        return {
            "success": True,
            "run_id": run_id,
            "status": status,
            "reason": reason,
            "documents": extraction_results,
            "ai_extractions": ai_results,
            "comparisons": comparison_results,
            "validations": validation_results
        }

    except Exception as exc:

        try:
            add_execution_event(
                run_id,
                "Workflow",
                "Failed",
                str(exc)
            )

            update_run(
                run_id,
                "Processing Error",
                str(exc)
            )

        except Exception:
            pass

        return {
            "success": False,
            "run_id": run_id,
            "status": "Processing Error",
            "reason": str(exc),
            "documents": [],
            "ai_extractions": [],
            "comparisons": [],
            "validations": []
        }
