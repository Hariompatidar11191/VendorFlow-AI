
from modules.llm_provider import generate_response


prompt = """
You are testing VendorFlow AI.

Return a JSON object with:
{
    "company_name": "ABC Technologies Pvt Ltd",
    "document_type": "PAN",
    "extraction_status": "TEST_SUCCESS"
}

Return only JSON.
"""

print("\n========== VENDORFLOW AI LLM TEST ==========\n")

result = generate_response(prompt)

if result["success"]:

    print("STATUS: SUCCESS")
    print("PROVIDER:", result["provider"])
    print("MODEL:", result["model"])

    if result.get("fallback_used"):
        print("FALLBACK: YES")
    else:
        print("FALLBACK: NO")

    print("\nMODEL RESPONSE:")
    print(result["text"])

else:

    print("STATUS: FAILED")
    print("\nERROR DETAILS:")

    for error in result["errors"]:
        print(error)

print("\n============================================")
