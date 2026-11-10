# VendorFlow AI

A modular vendor onboarding and compliance automation project.

## Current milestone (v0.1)
- Streamlit application shell
- Vendor intake form
- PDF/image upload and local file persistence
- SQLite persistence for vendors, runs, documents and execution events
- Database-backed overview and run history

**Important:** This milestone does not yet extract document contents, call an LLM, verify identities, or make approval decisions. Those will be implemented in later milestones.

## Setup (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Add API credentials to `.env` only when LLM integration is implemented. Never commit `.env`.

## Current upload support
PDF, PNG, JPG and JPEG. Uploaded files are stored under `uploads/<run_id>/`.
