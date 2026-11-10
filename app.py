import streamlit as st
import pandas as pd
import tempfile

from pathlib import Path

from database.database import (
    init_db,
    create_vendor_submission,
    get_recent_runs,
    get_run_events,
    get_run_validations
)

from modules.document_processor import extract_documents
from modules.document_ai import extract_document_data
from modules.workflow_engine import process_vendor
from modules.ui_theme import apply_theme, render_sidebar, render_overview


# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="VendorFlow AI",
    page_icon="🏢",
    layout="wide"
)

init_db()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "last_run_id": None,
    "last_result": None,
    "pending_ai_results": None,
    "pending_uploads": None,
    "pending_manual": {},
    "confirmed_ai_results": None
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# UI THEME AND SIDEBAR
# ============================================================

apply_theme()

page = render_sidebar()


# ============================================================
# OVERVIEW DASHBOARD
# ============================================================

if page == "Overview":

    render_overview(get_recent_runs(1000))


# ============================================================
# NEW VENDOR SUBMISSION
# ============================================================

elif page == "New Vendor":

    st.title("New Vendor Registration")

    st.caption(
        "Upload vendor documents. Manual information is optional. "
        "AI will extract the available details."
    )

    # --------------------------------------------------------
    # STAGE 1: DOCUMENT UPLOAD AND OPTIONAL MANUAL INFORMATION
    # --------------------------------------------------------

    st.subheader("1. Vendor Documents and Optional Details")

    with st.form("vendor_upload_form"):

        documents = st.file_uploader(
            "Upload PAN, GST certificate and bank proof",
            type=["pdf"],
            accept_multiple_files=True
        )

        st.caption(
            "Machine-readable and scanned PDFs are supported. "
            "Scanned pages are processed using OCR before AI analysis."
        )

        st.divider()

        st.subheader("Optional Manual Information")

        col1, col2 = st.columns(2)

        with col1:

            company = st.text_input(
                "Legal Company Name"
            )

            contact = st.text_input(
                "Contact Person"
            )

            email = st.text_input(
                "Business Email"
            )

            pan = st.text_input(
                "PAN"
            )

        with col2:

            gstin = st.text_input(
                "GSTIN"
            )

            account = st.text_input(
                "Bank Account Number"
            )

            ifsc = st.text_input(
                "IFSC"
            )

            country = st.text_input(
                "Country",
                value="India"
            )

        analyze = st.form_submit_button(
            "Analyze Documents with AI",
            type="primary",
            use_container_width=True
        )

    # --------------------------------------------------------
    # STAGE 2: DOCUMENT EXTRACTION AND AI ANALYSIS
    # --------------------------------------------------------

    if analyze:

        if not documents:

            st.error(
                "Please upload at least one supporting PDF document."
            )

        else:

            manual_data = {
                "company_name": company.strip(),
                "contact_name": contact.strip(),
                "email": email.strip(),
                "pan": pan.strip().upper(),
                "gstin": gstin.strip().upper(),
                "bank_account": account.strip(),
                "ifsc": ifsc.strip().upper(),
                "country": country.strip()
            }

            ai_results = []

            try:

                with st.status(
                    "Starting document processing...",
                    expanded=True
                ) as status:

                    # STEP 1: Save uploaded documents
                    st.write("Step 1: Saving uploaded PDFs...")

                    with tempfile.TemporaryDirectory() as temp_dir:

                        paths = []

                        for index, uploaded in enumerate(documents):

                            file_path = (
                                Path(temp_dir)
                                / f"{index}_{Path(uploaded.name).name}"
                            )

                            file_path.write_bytes(uploaded.getvalue())
                            paths.append(str(file_path))

                        st.write(
                            f"Successfully saved {len(paths)} documents."
                        )

                        # STEP 2: Extract PDF text
                        st.write("Step 2: Extracting PDF text...")

                        extraction_results = extract_documents(paths)

                        st.write(
                            f"PDF extraction finished for "
                            f"{len(extraction_results)} documents."
                        )

                        # STEP 3: Analyze every PDF page independently
                        st.write(
                            "Step 3: Classifying and extracting "
                            "information from every PDF page..."
                        )

                        total_pages = sum(
                            len(item.get("page_results", []))
                            for item in extraction_results
                            if item.get("success")
                        )

                        processed_pages = 0

                        for index, item in enumerate(extraction_results):

                            filename = item.get(
                                "filename",
                                f"Document {index + 1}"
                            )

                            if not item.get("success"):

                                ai_results.append({
                                    "success": False,
                                    "filename": filename,
                                    "error": item.get(
                                        "error",
                                        "PDF extraction failed."
                                    )
                                })

                                continue

                            page_results = item.get("page_results", [])

                            # Backward compatibility if page_results
                            # are unavailable.
                            if not page_results and item.get("text"):
                                page_results = [{
                                    "page_number": 1,
                                    "text": item["text"],
                                    "success": True
                                }]

                            for page in page_results:

                                page_number = page.get(
                                    "page_number",
                                    processed_pages + 1
                                )

                                page_text = page.get("text", "").strip()

                                processed_pages += 1

                                page_label = (
                                    f"{filename} - Page {page_number}"
                                )

                                st.write(
                                    f"Analyzing page "
                                    f"{processed_pages}/{total_pages}: "
                                    f"{page_label}"
                                )

                                if not page.get("success") or not page_text:

                                    ai_results.append({
                                        "success": False,
                                        "filename": page_label,
                                        "source_filename": filename,
                                        "page_number": page_number,
                                        "error": "No readable text found on this page."
                                    })

                                    continue

                                try:

                                    result = extract_document_data(
                                        document_text=page_text,
                                        filename=page_label
                                    )

                                    result["filename"] = page_label
                                    result["source_filename"] = filename
                                    result["page_number"] = page_number

                                    ai_results.append(result)

                                    if result.get("success"):

                                        st.write(
                                            f"Extraction completed: "
                                            f"{page_label}"
                                        )

                                    else:

                                        st.warning(
                                            f"AI extraction failed: "
                                            f"{page_label}"
                                        )

                                except Exception as exc:

                                    ai_results.append({
                                        "success": False,
                                        "filename": page_label,
                                        "source_filename": filename,
                                        "page_number": page_number,
                                        "error": str(exc)
                                    })

                                    st.warning(
                                        f"Could not process {page_label}: {exc}"
                                    )

                    # Preserve results
                    st.session_state["pending_uploads"] = documents
                    st.session_state["pending_manual"] = manual_data
                    st.session_state["pending_ai_results"] = ai_results

                    status.update(
                        label="Document analysis completed!",
                        state="complete",
                        expanded=True
                    )

                st.success(
                    "Document analysis completed. "
                    "Review the extracted information below."
                )

            except Exception as exc:

                st.error(
                    f"Document processing failed: {exc}"
                )

                st.exception(exc)

    # --------------------------------------------------------
    # STAGE 3: DISPLAY AI EXTRACTION RESULTS
    # --------------------------------------------------------

    ai_results = st.session_state.get(
        "pending_ai_results"
    )

    if ai_results is not None:

        st.divider()

        st.subheader("2. AI Document Extraction Results")

        extracted_values = {
            "company_name": [],
            "contact_name": [],
            "pan": [],
            "gstin": [],
            "bank_account": [],
            "ifsc": []
        }

        for result in ai_results:

            filename = result.get(
                "filename",
                "Uploaded document"
            )

            with st.expander(
                filename,
                expanded=True
            ):

                if result.get("success"):

                    data = result.get("data", {})

                    st.success(
                        "Document identified: "
                        f"{data.get('document_type', 'UNKNOWN')}"
                    )

                    st.caption(
                        f"Provider: {result.get('provider')} | "
                        f"Model: {result.get('model')} | "
                        f"Fallback: {result.get('fallback', False)}"
                    )

                    field_mapping = {
                        "company_name": "company_name",
                        "contact_name": "person_name",
                        "pan": "pan",
                        "gstin": "gstin",
                        "bank_account": "account_number",
                        "ifsc": "ifsc"
                    }

                    for target, source in field_mapping.items():

                        value = data.get(source)

                        if value and str(value).strip():

                            extracted_values[target].append(
                                str(value).strip()
                            )

                    st.json(data)

                else:

                    st.warning(
                        result.get(
                            "error",
                            "Document extraction failed."
                        )
                    )

        # ----------------------------------------------------
        # DOCUMENT COVERAGE DASHBOARD
        # ----------------------------------------------------

        st.divider()
        st.subheader("3. Document Coverage Summary")

        # Track identified pages dynamically
        coverage = {
            "PAN": [],
            "GST": [],
            "BANK": []
        }

        unknown_pages = []
        failed_pages = []

        for index, result in enumerate(ai_results, start=1):

            filename = result.get(
                "filename",
                f"Page {index}"
            )

            if not result.get("success"):
                failed_pages.append(filename)
                continue

            data = result.get("data", {})

            document_type = str(
                data.get("document_type", "UNKNOWN")
            ).strip().upper()

            normalized_type = (
                document_type.replace("-", "_")
                .replace(" ", "_")
            )

            if normalized_type in ["PAN", "PAN_CARD", "PAN_PROOF"]:
                coverage["PAN"].append(filename)

            elif normalized_type in [
                "GST", "GSTIN", "GST_CERTIFICATE",
                "GST_REGISTRATION"
            ]:
                coverage["GST"].append(filename)

            elif normalized_type in [
                "BANK", "BANK_PROOF", "BANK_STATEMENT",
                "CANCELLED_CHEQUE", "PASSBOOK"
            ]:
                coverage["BANK"].append(filename)

            else:
                unknown_pages.append(filename)

        total_pages = len(ai_results)

        identified_count = sum(
            len(pages) for pages in coverage.values()
        )

        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Pages Processed", total_pages)
        c2.metric("Classified Pages", identified_count)
        c3.metric("Unknown Pages", len(unknown_pages))
        c4.metric("Failed Pages", len(failed_pages))

        st.markdown("#### Required Document Coverage")

        coverage_columns = st.columns(3)

        for column, document_type in zip(
            coverage_columns,
            ["PAN", "GST", "BANK"]
        ):

            pages = coverage[document_type]

            with column:

                if pages:
                    st.success(
                        f"**{document_type} — FOUND**"
                    )
                else:
                    st.error(
                        f"**{document_type} — MISSING**"
                    )

                st.metric(
                    "Pages identified",
                    len(pages)
                )

                if pages:
                    for page_name in pages:
                        st.caption(f"• {page_name}")

                    if len(pages) > 1:
                        st.caption(
                            f"{len(pages) - 1} additional "
                            "matching page(s)"
                        )

        if unknown_pages or failed_pages:

            st.markdown("#### Pages Requiring Manual Review")

            for filename in unknown_pages:
                st.warning(
                    f"Unclassified: {filename}"
                )

            for filename in failed_pages:
                st.error(
                    f"Extraction failed: {filename}"
                )

        else:
            st.success(
                "All processed pages have recognized document types."
            )

        # ----------------------------------------------------
        # STAGE 4: MERGE MANUAL AND EXTRACTED VALUES
        # ----------------------------------------------------

        st.divider()

        st.subheader("4. Merge and Review Information")

        manual_data = st.session_state.get(
            "pending_manual",
            {}
        )

        merged = {}

        field_labels = {
            "company_name": "Legal Company Name",
            "contact_name": "Contact Person",
            "email": "Business Email",
            "pan": "PAN",
            "gstin": "GSTIN",
            "bank_account": "Bank Account Number",
            "ifsc": "IFSC",
            "country": "Country"
        }

        conflicting_fields = []

        for field, label in field_labels.items():

            manual_value = manual_data.get(field, "")

            # Remove duplicate extracted values irrespective of capitalization
            raw_values = extracted_values.get(field, [])

            values = []
            seen = set()

            for value in raw_values:

                normalized = " ".join(
                    value.strip().casefold().split()
                )

                if normalized not in seen:
                    seen.add(normalized)
                    values.append(value.strip())

            if manual_value:

                merged[field] = manual_value

                if values and any(
                    value.upper() != manual_value.upper()
                    for value in values
                ):
                    conflicting_fields.append(label)

            elif len(values) == 1:

                merged[field] = values[0]

            elif len(values) > 1:

                merged[field] = ""
                conflicting_fields.append(label)

            else:

                merged[field] = ""

        if not merged.get("country"):
            merged["country"] = "India"

        if conflicting_fields:

            st.warning(
                "Please carefully review these fields because "
                "manual and extracted values differ or multiple "
                "documents contain conflicting values: "
                + ", ".join(conflicting_fields)
            )

        # ----------------------------------------------------
        # STAGE 5: EDITABLE REVIEW FORM
        # ----------------------------------------------------

        st.subheader("5. Confirm Vendor Information")

        st.info(
            "All fields below are editable. Correct any extraction "
            "mistakes before submitting the vendor."
        )

        with st.form("vendor_review_form"):

            col1, col2 = st.columns(2)

            with col1:

                final_company = st.text_input(
                    "Legal Company Name *",
                    value=merged["company_name"]
                )

                final_contact = st.text_input(
                    "Contact Person",
                    value=merged["contact_name"]
                )

                final_email = st.text_input(
                    "Business Email",
                    value=merged["email"]
                )

                final_pan = st.text_input(
                    "PAN",
                    value=merged["pan"]
                )

            with col2:

                final_gstin = st.text_input(
                    "GSTIN",
                    value=merged["gstin"]
                )

                final_account = st.text_input(
                    "Bank Account Number",
                    value=merged["bank_account"]
                )

                final_ifsc = st.text_input(
                    "IFSC",
                    value=merged["ifsc"]
                )

                final_country = st.text_input(
                    "Country",
                    value=merged["country"]
                )

            confirm = st.form_submit_button(
                "Confirm Details and Submit Vendor",
                type="primary",
                use_container_width=True
            )

        # ----------------------------------------------------
        # STAGE 6: SAVE CONFIRMED SUBMISSION AND RUN WORKFLOW
        # ----------------------------------------------------

        if confirm:

            if not final_company.strip():

                st.error(
                    "Company name is required. "
                    "Enter it manually or ensure it can be extracted "
                    "from an uploaded document."
                )

            elif not st.session_state.get("pending_uploads"):

                st.error(
                    "Uploaded documents are no longer available. "
                    "Please upload the documents again."
                )

            else:

                vendor_data = {
                    "company_name": final_company.strip(),
                    "contact_name": final_contact.strip(),
                    "email": final_email.strip(),
                    "pan": final_pan.strip().upper(),
                    "gstin": final_gstin.strip().upper(),
                    "bank_account": final_account.strip(),
                    "ifsc": final_ifsc.strip().upper(),
                    "country": final_country.strip()
                }

                try:

                    with st.spinner(
                        "Saving confirmed vendor submission..."
                    ):

                        run_id = create_vendor_submission(
                            vendor_data,
                            st.session_state["pending_uploads"]
                        )

                    st.success(
                        f"Vendor submission created: {run_id}"
                    )

                    # Preserve AI results before executing workflow.
                    st.session_state["confirmed_ai_results"] = (
                        ai_results
                    )

                    with st.spinner(
                        "Running vendor verification workflow..."
                    ):

                        result = process_vendor(
                            run_id,
                            precomputed_ai_results=st.session_state[
                                "confirmed_ai_results"
                            ]
                        )

                    st.session_state["last_run_id"] = run_id

                    st.session_state["last_result"] = result

                    # Clear temporary review state.
                    st.session_state["pending_ai_results"] = None

                    st.session_state["pending_uploads"] = None

                    st.session_state["pending_manual"] = {}

                    st.session_state["confirmed_ai_results"] = None

                    if result["success"]:

                        st.success(
                            "Workflow completed. Preliminary status: "
                            f"{result['status']}"
                        )

                        st.info(
                            "Open Live Execution to inspect AI extraction "
                            "and validation results."
                        )

                    else:

                        st.error(
                            f"Workflow failed: {result['reason']}"
                        )

                except Exception as exc:

                    st.error(
                        f"Submission error: {exc}"
                    )


# ============================================================
# LIVE EXECUTION MONITOR
# ============================================================

elif page == "Live Execution":

    st.title("Workflow Execution Monitor")

    run_id = st.session_state.get("last_run_id")

    if not run_id:

        st.info(
            "Submit a vendor first to inspect its execution."
        )

    else:

        st.caption(
            f"Execution ID: {run_id}"
        )

        events = get_run_events(run_id)

        st.subheader("Execution Timeline")

        for event in events:

            with st.expander(
                f"{event['stage']} — {event['status']}",
                expanded=True
            ):

                st.write(event["details"])

                st.caption(
                    event["created_at"]
                )

        validations = get_run_validations(run_id)

        st.subheader("Validation Results")

        if validations:

            st.dataframe(
                pd.DataFrame(validations),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No validation results recorded."
            )

        result = st.session_state.get("last_result")

        if result:

            # ----------------------------------------------------
            # STAGE 6: LIVE EXECUTION INSIGHTS
            # ----------------------------------------------------

            st.divider()
            st.subheader("Execution Insights")

            ai_results = result.get("ai_extractions", [])

            # Document coverage: classify successful AI page results.
            coverage = {"PAN": [], "GST": [], "BANK": []}
            unknown_pages = []
            failed_pages = []

            document_aliases = {
                "PAN": {"PAN", "PAN_CARD", "PAN_PROOF"},
                "GST": {"GST", "GSTIN", "GST_CERTIFICATE", "GST_REGISTRATION"},
                "BANK": {
                    "BANK", "BANK_PROOF", "BANK_STATEMENT",
                    "CANCELLED_CHEQUE", "PASSBOOK"
                },
            }

            for index, item in enumerate(ai_results, start=1):
                filename = item.get("filename", f"Page {index}")

                if not item.get("success"):
                    failed_pages.append(filename)
                    continue

                data = item.get("data", {})
                doc_type = str(data.get("document_type", "UNKNOWN")).strip().upper()
                normalized_type = doc_type.replace("-", "_").replace(" ", "_")

                matched_type = next(
                    (
                        category
                        for category, aliases in document_aliases.items()
                        if normalized_type in aliases
                    ),
                    None,
                )

                if matched_type:
                    coverage[matched_type].append(filename)
                else:
                    unknown_pages.append(filename)

            total_pages = len(ai_results)
            classified_pages = sum(len(pages) for pages in coverage.values())
            duplicate_pages = sum(max(len(pages) - 1, 0) for pages in coverage.values())
            missing_documents = [
                name for name, pages in coverage.items() if not pages
            ]

            st.markdown("#### Document coverage")

            cov1, cov2, cov3, cov4 = st.columns(4)
            cov1.metric("Pages analyzed", total_pages)
            cov2.metric("Classified pages", classified_pages)
            cov3.metric("Duplicate pages", duplicate_pages)
            cov4.metric("Unknown / failed", len(unknown_pages) + len(failed_pages))

            doc_cols = st.columns(3)
            for column, document_type in zip(doc_cols, ["PAN", "GST", "BANK"]):
                pages = coverage[document_type]
                with column:
                    if pages:
                        st.success(f"{document_type} — RECEIVED")
                    else:
                        st.error(f"{document_type} — MISSING")
                    st.metric("Matching pages", len(pages))
                    if len(pages) > 1:
                        st.caption(
                            f"{len(pages) - 1} additional matching page(s); "
                            "review for duplicates."
                        )
                    elif pages:
                        st.caption(pages[0])

            if unknown_pages:
                with st.expander(f"Unknown document pages ({len(unknown_pages)})"):
                    for filename in unknown_pages:
                        st.warning(filename)

            if failed_pages:
                with st.expander(f"Failed AI extraction pages ({len(failed_pages)})"):
                    for filename in failed_pages:
                        st.error(filename)

            if missing_documents:
                st.warning(
                    "Required document types not identified: "
                    + ", ".join(missing_documents)
                )
            elif not unknown_pages and not failed_pages:
                st.success("PAN, GST and bank document types were all identified.")

            # Validation scorecard from workflow result; DB results remain visible above.
            validation_items = result.get("validations", []) or validations
            pass_count = sum(
                str(item.get("result", "")).upper() == "PASS"
                for item in validation_items
            )
            fail_count = sum(
                str(item.get("result", "")).upper() == "FAIL"
                for item in validation_items
            )
            missing_count = sum(
                str(item.get("result", "")).upper() == "MISSING"
                for item in validation_items
            )

            st.markdown("#### Validation scorecard")
            val1, val2, val3, val4 = st.columns(4)
            val1.metric("Total checks", len(validation_items))
            val2.metric("Passed", pass_count)
            val3.metric("Failed", fail_count)
            val4.metric("Missing", missing_count)

            if validation_items:
                scorecard_df = pd.DataFrame(validation_items)
                preferred_columns = [
                    column for column in ["check_name", "result", "details"]
                    if column in scorecard_df.columns
                ]
                if preferred_columns:
                    st.dataframe(
                        scorecard_df[preferred_columns],
                        use_container_width=True,
                        hide_index=True,
                    )

            # AI provider and fallback summary.
            successful_ai = [item for item in ai_results if item.get("success")]
            providers = sorted({
                str(item.get("provider"))
                for item in successful_ai
                if item.get("provider")
            })
            models = sorted({
                str(item.get("model"))
                for item in successful_ai
                if item.get("model")
            })
            fallback_count = sum(
                bool(item.get("fallback", False)) for item in successful_ai
            )

            st.markdown("#### AI extraction summary")
            ai1, ai2, ai3 = st.columns(3)
            ai1.metric("Successful extractions", len(successful_ai))
            ai2.metric("Fallback extractions", fallback_count)
            ai3.metric("AI extraction failures", len(failed_pages))
            st.caption(
                f"Provider(s): {', '.join(providers) if providers else 'Not recorded'}"
            )
            st.caption(
                f"Model(s): {', '.join(models) if models else 'Not recorded'}"
            )

            st.divider()

            st.subheader("Final Decision")

            decision_status = result.get("status", "Unknown")

            if decision_status == "Approved":
                st.success(f"Preliminary decision: {decision_status}")
            elif decision_status == "Pending":
                st.warning(f"Preliminary decision: {decision_status}")
            elif decision_status == "Rejected":
                st.error(f"Preliminary decision: {decision_status}")
            else:
                st.info(f"Preliminary decision: {decision_status}")

            st.markdown("**Decision explanation**")

            st.write(
                result.get(
                    "reason",
                    "No decision explanation was recorded."
                )
            )

            st.subheader("PDF Text Extraction Results")

            for document in result.get("documents", []):

                with st.expander(
                    document.get("filename", "Document")
                ):

                    if document.get("success"):

                        st.write(
                            f"Pages: {document.get('pages', 'N/A')}"
                        )

                        st.write(
                            document.get("text", "")[:5000]
                            or "No machine-readable text found."
                        )

                        if document.get("needs_ocr"):

                            st.warning(
                                "This PDF appears to require OCR."
                            )

                    else:

                        st.error(
                            document.get(
                                "error",
                                "Document processing failed."
                            )
                        )

            # Show structured AI extraction results.
            st.subheader("AI Extracted Information")

            for ai_result in result.get("ai_extractions", []):

                with st.expander(
                    ai_result.get("filename", "AI extraction")
                ):

                    if ai_result.get("success"):

                        st.caption(
                            f"Provider: {ai_result.get('provider')} | "
                            f"Model: {ai_result.get('model')} | "
                            f"Fallback: {ai_result.get('fallback', False)}"
                        )

                        st.json(
                            ai_result.get("data", {})
                        )

                    else:

                        st.warning(
                            ai_result.get(
                                "error",
                                "AI extraction failed."
                            )
                        )


# ============================================================
# RUN HISTORY
# ============================================================

elif page == "Run History":

    st.title("Vendor Processing History")

    runs = get_recent_runs(1000)

    if runs:

        df = pd.DataFrame(runs)

        status_filter = st.selectbox(
            "Filter by status",
            [
                "All",
                "Submitted",
                "Approved",
                "Pending",
                "Rejected",
                "Processing Error"
            ]
        )

        if status_filter != "All":

            df = df[
                df["status"] == status_filter
            ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No processing history available."
        )