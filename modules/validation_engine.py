
import re


def validate_pan(pan):
    if not pan:
        return "MISSING", "PAN was not provided"

    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]$"

    if re.fullmatch(pattern, pan.upper()):
        return "PASS", "PAN format is valid"

    return "FAIL", "Invalid PAN format"


def validate_gstin(gstin):
    if not gstin:
        return "MISSING", "GSTIN was not provided"

    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"

    if re.fullmatch(pattern, gstin.upper()):
        return "PASS", "GSTIN format is valid"

    return "FAIL", "Invalid GSTIN format"


def validate_ifsc(ifsc):
    if not ifsc:
        return "MISSING", "IFSC was not provided"

    pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"

    if re.fullmatch(pattern, ifsc.upper()):
        return "PASS", "IFSC format is valid"

    return "FAIL", "Invalid IFSC format"




def validate_vendor(vendor, documents, ai_results=None):

    results = []

    # -----------------------------------------
    # 1. Validate vendor field formats
    # -----------------------------------------

    checks = [
        ("PAN", validate_pan(vendor.get("pan"))),
        ("GSTIN", validate_gstin(vendor.get("gstin"))),
        ("IFSC", validate_ifsc(vendor.get("ifsc")))
    ]

    for name, (status, message) in checks:
        results.append({
            "check_name": name,
            "result": status,
            "details": message
        })

    # -----------------------------------------
    # 2. Classify pages using AI document_type
    # -----------------------------------------

    identified_pages = {
        "pan": [],
        "gst": [],
        "bank": []
    }

    unclassified_pages = []
    failed_pages = []

    for index, ai_result in enumerate(ai_results or [], start=1):

        filename = ai_result.get(
            "filename",
            f"Page {index}"
        )

        if not ai_result.get("success"):
            failed_pages.append(filename)
            continue

        data = ai_result.get("data", {})

        document_type = str(
            data.get("document_type") or "UNKNOWN"
        ).strip().upper()

        # Accept the canonical types and common explicit variants.
        normalized_type = document_type.replace("-", "_").replace(" ", "_")

        if normalized_type in ["PAN", "PAN_CARD", "PAN_PROOF"]:
            identified_pages["pan"].append(filename)

        elif normalized_type in [
            "GST", "GSTIN", "GST_CERTIFICATE", "GST_REGISTRATION"
        ]:
            identified_pages["gst"].append(filename)

        elif normalized_type in [
            "BANK", "BANK_PROOF", "BANK_STATEMENT",
            "CANCELLED_CHEQUE", "PASSBOOK"
        ]:
            identified_pages["bank"].append(filename)

        else:
            unclassified_pages.append(filename)

    # -----------------------------------------
    # 3. Validate required document coverage
    # -----------------------------------------

    required_document_types = {
        "PAN proof": "pan",
        "GST certificate": "gst",
        "Bank proof": "bank"
    }

    for document_name, document_type in required_document_types.items():

        pages = identified_pages[document_type]

        if pages:
            result = "PASS"

            details = (
                f"Document identified on {len(pages)} page(s): "
                + ", ".join(pages)
            )

            if len(pages) > 1:
                details += (
                    f". {len(pages) - 1} additional "
                    "matching page(s) detected."
                )

        else:
            result = "MISSING"
            details = "Required document not identified by AI."

        results.append({
            "check_name": document_name,
            "result": result,
            "details": details
        })

    # -----------------------------------------
    # 4. Flag unclassified and failed pages
    # -----------------------------------------

    if unclassified_pages or failed_pages:

        page_messages = []

        if unclassified_pages:
            page_messages.append(
                "Unclassified pages: "
                + ", ".join(unclassified_pages)
            )

        if failed_pages:
            page_messages.append(
                "AI extraction failures: "
                + ", ".join(failed_pages)
            )

        results.append({
            "check_name": "Unclassified / Failed Pages",
            "result": "MISSING",
            "details": (
                "; ".join(page_messages)
                + ". Manual review required."
            )
        })

    else:
        results.append({
            "check_name": "Page Classification",
            "result": "PASS",
            "details": (
                "All submitted AI-processed pages received "
                "a recognized document classification."
            )
        })

    return results
