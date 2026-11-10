# VendorFlow AI

AI-assisted vendor onboarding and preliminary compliance review built with **Python, Streamlit, SQLite, document processing, OCR, and LLM-based information extraction**.

VendorFlow AI helps an operations team collect vendor information, read supporting PDF documents, review extracted fields, run configurable validation checks, and inspect the execution history of each submission.

> **Important:** VendorFlow AI provides preliminary, software-based checks. It does not perform authoritative PAN, GST, identity, bank-account, or IFSC verification. A final business decision must include the organization's required manual and external verification processes.

## Features

- **Vendor submission:** Upload supporting PDF documents and optionally enter vendor details manually.
- **PDF text extraction:** Extract text from uploaded PDFs; scanned pages can be processed using OCR.
- **Page-level AI extraction:** Classify and extract information from individual document pages.
- **Human review:** Review and edit AI-extracted information before submitting the vendor.
- **Conflict handling:** Manual values take precedence; conflicting or ambiguous extracted values are surfaced for review.
- **Document coverage:** Track whether PAN, GST and bank-proof document types were identified, and surface unknown or failed pages.
- **Validation workflow:** Run field-format, required-document and document-to-form comparison checks.
- **AI provider fallback:** Use the configured Gemini-first provider flow with Cloudflare Workers AI fallback.
- **Execution monitoring:** Inspect workflow events, extraction results, validation outcomes and the preliminary decision.
- **Run history and overview:** Review previous submissions and high-level processing statistics.
- **SQLite persistence:** Store vendor submissions and workflow records locally.

## Application workflow

1. The user uploads vendor PDFs and optionally enters vendor details.
2. The application extracts PDF text and uses OCR when needed.
3. AI analyzes each readable page and returns structured document information.
4. The user reviews and edits the merged vendor information.
5. The user confirms the submission.
6. The workflow compares extracted identifiers with submitted values and runs validation checks.
7. VendorFlow AI records a preliminary status: `Approved`, `Pending`, `Rejected`, or `Processing Error`.
8. The user reviews the execution timeline and validation report.

## Technology stack

| Area | Technologies |
|---|---|
| User interface | Python, Streamlit |
| Data handling | pandas |
| Database | SQLite |
| PDF processing | PyMuPDF (fitz) |
| OCR | Tesseract OCR, pytesseract |
| AI extraction | Google Gemini API |
| AI fallback | Cloudflare Workers AI |
| Dashboard and charts | Altair, Streamlit |
| Validation | Python, regular expressions |
| Configuration | Environment variables / Streamlit secrets |

The exact model names and configuration variable names are determined by the current provider modules and deployment configuration.

## Project structure

The application code is organized around the following modules. Adjust this tree if your repository contains additional files or different filenames.

```text
vendorflow_ai/
├── app.py
├── requirements.txt
├── packages.txt                 # Optional: system packages for Streamlit Cloud
├── database/
│   └── database.py
└── modules/
    ├── ui_theme.py
    ├── document_processor.py
    ├── document_ai.py
    ├── workflow_engine.py
    ├── validation_engine.py
    ├── llm_provider.py
    ├── gemini_client.py
    └── cloudflare_client.py
```

## Run locally

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

If the repository includes `requirements.txt`:

```bash
pip install -r requirements.txt
```

If it does not, create it from the project's actual imports and installed packages before deployment. Do not use guessed or unpinned production dependencies.

### 4. Install Tesseract OCR

Tesseract is a system dependency and is separate from the Python package `pytesseract`.

- **Windows:** Install Tesseract OCR and ensure `tesseract.exe` is available on `PATH`. If the application configures an explicit executable path, use the path expected by that code.
- **Ubuntu / Debian:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`

If OCR is unavailable, scanned PDFs may not be readable by the extraction pipeline.

### 5. Configure API credentials

Configure the API credentials required by the provider modules. Keep credentials out of source code and never commit `.env` files or API keys.

For local development, use the environment-variable names read by the current files in `modules/gemini_client.py` and `modules/cloudflare_client.py`. The exact names should be copied from those modules rather than guessed.

### 6. Start the application

```bash
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`.

## Deploy on Streamlit Community Cloud

1. Push the project to a GitHub repository.
2. Confirm that `app.py`, `requirements.txt`, the `database/` folder and the `modules/` folder are committed.
3. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
4. Select **Create app**, choose the repository and branch, and set the main file path to `app.py`.
5. Add the provider credentials under the app's **Settings → Secrets** using the exact variable names expected by the provider modules.
6. Deploy the app and review the deployment logs for missing Python packages, system dependencies or configuration errors.

### OCR deployment note

Streamlit Community Cloud installs Python packages from `requirements.txt`. System packages such as Tesseract may require a `packages.txt` file in the repository root. If the app depends on Tesseract OCR in the cloud, add the appropriate OS package entry, for example:

```text
tesseract-ocr
```

Verify OCR on the deployed app with a scanned PDF. A successful deployment does not by itself prove that OCR is installed or working.

### Secrets and deployment safety

- Never put API keys directly in `app.py` or other committed files.
- Never commit `.env`, credentials, database files containing real vendor information, or uploaded confidential documents.
- Use Streamlit secrets for deployed credentials.
- Restrict access to the deployed application if it will process real vendor documents.
- Review Streamlit Community Cloud storage and persistence behavior before relying on a local SQLite database for production records. Local app storage should not be treated as a durable production database without verifying the hosting platform's persistence guarantees.

## Validation and decision interpretation

The workflow records validation outcomes such as `PASS`, `FAIL` and `MISSING`. It then produces a preliminary status:

- **Approved:** Implemented preliminary checks passed. This is not official verification of the vendor's identity, tax registration or bank account.
- **Pending:** Required information is missing or processing/manual review is still needed.
- **Rejected:** One or more implemented checks produced a failure, such as a document-to-form mismatch.
- **Processing Error:** The workflow encountered an execution error.

A document being classified as PAN, GST or BANK only indicates that the AI identified that document type. It does not establish that the document is genuine or currently valid.

## Suggested demo scenarios

Use synthetic or appropriately redacted documents and test data.

1. PAN + GST + bank proof supplied, with matching form details.
2. Bank proof missing.
3. PAN or GSTIN differs between the form and uploaded document.
4. Contact person missing.
5. Multiple pages classified as the same document type.
6. Unknown document type or unreadable page.
7. Corrupted PDF or PDF extraction failure.
8. Primary AI provider failure, followed by the configured fallback path.

## Limitations

- AI-extracted values can be incomplete or incorrect and must be reviewed.
- OCR quality depends on scan resolution, orientation, contrast and document quality.
- Document classification is not document authenticity verification.
- Regex and format checks do not confirm that identifiers are active or belong to the vendor.
- External PAN, GST and bank verification requires authorized services and credentials that are not implied by this application.
- SQLite/local file persistence may not be suitable for concurrent or production workloads without an appropriate deployment and backup strategy.

## Future improvements

- Integrate authorized external verification services where available.
- Add role-based access control and reviewer approvals.
- Add secure object storage for uploaded documents.
- Add audit logging, retention controls and database backups.
- Add automated tests for extraction, validation and provider fallback.
- Add monitoring for API latency, token usage and provider errors.

## Responsible use and data protection

Vendor documents can contain sensitive personal and financial information. Use synthetic or redacted data for demonstrations. Before processing real vendor records, establish access controls, consent and lawful processing, retention/deletion procedures, secure storage, and appropriate organizational approval.


