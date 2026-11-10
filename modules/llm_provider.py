
from modules.gemini_client import GeminiClient
from modules.cloudflare_client import CloudflareClient


class LLMProvider:

    def __init__(self):
        self.gemini = None
        self.cloudflare = None

    def generate(self, prompt):

        errors = []

        # --------------------------------
        # 1. Try Gemini models
        # --------------------------------

        try:
            if self.gemini is None:
                self.gemini = GeminiClient()

            result = self.gemini.generate(prompt)

            if result["success"]:
                return result

            errors.extend(result["errors"])

        except Exception as exc:
            errors.append({
                "provider": "Gemini",
                "error": str(exc)
            })

        # --------------------------------
        # 2. Fallback to Cloudflare
        # --------------------------------

        try:
            if self.cloudflare is None:
                self.cloudflare = CloudflareClient()

            result = self.cloudflare.generate(prompt)

            if result["success"]:
                result["fallback_used"] = True
                result["previous_errors"] = errors
                return result

            errors.append({
                "provider": "Cloudflare",
                "error": result.get("error")
            })

        except Exception as exc:
            errors.append({
                "provider": "Cloudflare",
                "error": str(exc)
            })

        # --------------------------------
        # 3. All providers failed
        # --------------------------------

        return {
            "success": False,
            "provider": None,
            "model": None,
            "text": None,
            "errors": errors
        }


def generate_response(prompt):

    provider = LLMProvider()
    return provider.generate(prompt)
