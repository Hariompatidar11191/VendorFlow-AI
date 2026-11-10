
import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Local .env values are loaded without overriding deployment-provided values.
load_dotenv(override=False)


def get_config(key, default=None):
    """Read configuration from environment variables or Streamlit secrets."""
    value = os.getenv(key)

    if value:
        return value

    try:
        value = st.secrets.get(key, default)
    except Exception:
        value = default

    return value if value not in (None, "") else default


class GeminiClient:

    def __init__(self):

        api_key = get_config("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")

        # 30-second request timeout and no automatic retries.
        http_options = types.HttpOptions(
            timeout=30000,
            retry_options=types.HttpRetryOptions(
                attempts=1
            )
        )

        self.client = genai.Client(
            api_key=api_key,
            http_options=http_options
        )

        self.models = [
            get_config("GEMINI_MODEL_1", "gemini-3.6-flash"),
            get_config("GEMINI_MODEL_2", "gemini-3.7-flash"),
            get_config("GEMINI_MODEL_3", "gemini-3.8-flash")
        ]

    def generate(self, prompt):

        errors = []

        for model in self.models:

            try:
                print(f"[Gemini] Trying model: {model}")

                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                text = response.text

                if not text:
                    raise ValueError("Empty response from Gemini")

                print(f"[Gemini] Success: {model}")

                return {
                    "success": True,
                    "provider": "Gemini",
                    "model": model,
                    "text": text,
                    "fallback": model != self.models[0],
                    "errors": errors
                }

            except Exception as exc:

                error = str(exc)

                print(f"[Gemini] Failed: {model} | {error}")

                errors.append({
                    "model": model,
                    "error": error
                })

        return {
            "success": False,
            "provider": None,
            "model": None,
            "text": None,
            "errors": errors
        }
