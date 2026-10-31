"""
Example External AI Client for Context Bank.
Demonstrates how an external AI application (e.g. Voxcent or any custom AI tool)
retrieves saved context using trigger words and prepares prompts for LLMs.

Usage:
    python scripts/client_example.py
"""
import sys
import httpx

BACKEND_URL = "http://127.0.0.1:8000"


def demonstrate_integration():
    print("=" * 60)
    print("Context Bank External AI Integration Demonstration")
    print("=" * 60)

    # 1. Health check
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/health")
        print(f"Backend status: {r.status_code} - {r.json()['service']} is online!")
    except Exception as e:
        print(f"Error connecting to backend: {e}")
        print("Please ensure the backend is running with:")
        print("    python -m uvicorn backend.main:app --port 8000")
        return

    # 2. Retrieve by prompt: 'Continue VOXCENT from where I stopped.'
    prompt_query = "Continue VOXCENT from where I stopped."
    print(f"\n[AI Client] User asks: \"{prompt_query}\"")
    print("[AI Client] Contacting Context Bank to resolve trigger in prompt...")

    resp = httpx.post(
        f"{BACKEND_URL}/api/v1/contexts/retrieve-prompt",
        json={
            "prompt": prompt_query,
            "detail_level": "summary_and_state",
            "output_format": "prompt",
        },
        timeout=10.0,
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n[AI Client] Successfully resolved trigger: {data['primary_trigger']}")
        print(f"[AI Client] Context Title: {data['title']}")
        print("\n--- INJECTED CONTEXT PACKAGE FOR AI MODEL ---")
        print(data["package_content"])
        print("---------------------------------------------\n")
        print("[AI Client] Ready to pass context into LLM (Gemini, Claude, or local model)!")
    elif resp.status_code == 404:
        print("[AI Client] No registered trigger recognized in prompt.")
    else:
        print(f"[AI Client] Error: {resp.status_code} - {resp.text}")


if __name__ == "__main__":
    demonstrate_integration()
