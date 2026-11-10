import os
import requests
import streamlit as st

from dotenv import load_dotenv

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


class CloudflareClient:

    def __init__(self):

        self.account_id = get_config("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = get_config("CLOUDFLARE_API_TOKEN")

        self.model = get_config(
            "CLOUDFLARE_MODEL",
            "@cf/openai/gpt-oss-120b"
        )

        if not self.account_id or not self.api_token:
            raise ValueError("Cloudflare credentials are missing")

        self.url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model}"
        )

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def generate(self, prompt):

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise document understanding "
                        "assistant. Return the requested structured output."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 3000,
            "temperature": 0.1
        }

        try:

            print("[Cloudflare] Starting fallback request...")

            response = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=(10, 45)
            )

            response.raise_for_status()

            data = response.json()

            if data.get("success") is False:
                raise RuntimeError(str(data.get("errors")))

            result = data.get("result", {})
            text = result.get("response")

            if not text and isinstance(result.get("choices"), list):
                choices = result["choices"]

                if choices:
                    text = choices[0].get(
                        "message", {}
                    ).get("content")

            if not text:
                raise ValueError("Cloudflare returned an empty response")

            print("[Cloudflare] Fallback successful.")

            return {
                "success": True,
                "provider": "Cloudflare",
                "model": self.model,
                "text": text
            }

        except Exception as exc:

            print(f"[Cloudflare] Failed: {exc}")

            return {
                "success": False,
                "provider": "Cloudflare",
                "model": self.model,
                "text": None,
                "error": str(exc)
            }
