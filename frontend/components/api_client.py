import os
from typing import Dict, Any, Optional, List
import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


class ContextBankAPI:
    """HTTP client wrapper communicating with the FastAPI backend."""

    def __init__(self, base_url: str = BACKEND_URL, token: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get_health(self) -> Dict[str, Any]:
        try:
            r = httpx.get(f"{self.base_url}/api/v1/health", timeout=3.0)
            return r.json() if r.status_code == 200 else {"status": "unreachable"}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def get_system_status(self) -> Dict[str, Any]:
        try:
            r = httpx.get(f"{self.base_url}/api/v1/integrations/status", headers=self._headers(), timeout=4.0)
            return r.json() if r.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "offline", "error": str(e)}

    def get_dashboard_stats(self) -> Dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/v1/integrations/dashboard-stats", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def list_contexts(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "updated_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        params = {"sort_by": sort_by, "page": page, "page_size": page_size}
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        if status:
            params["status"] = status
        r = httpx.get(f"{self.base_url}/api/v1/contexts", headers=self._headers(), params=params, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def get_context(self, context_id: str) -> Dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/v1/contexts/{context_id}", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def create_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        r = httpx.post(f"{self.base_url}/api/v1/contexts", headers=self._headers(), json=data, timeout=10.0)
        r.raise_for_status()
        return r.json()

    def update_context(self, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        r = httpx.patch(f"{self.base_url}/api/v1/contexts/{context_id}", headers=self._headers(), json=data, timeout=8.0)
        r.raise_for_status()
        return r.json()

    def delete_context(self, context_id: str) -> Dict[str, Any]:
        r = httpx.delete(f"{self.base_url}/api/v1/contexts/{context_id}", headers=self._headers(), timeout=6.0)
        r.raise_for_status()
        return r.json()

    def quick_lookup(self, trigger: str) -> Dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/v1/search/quick-lookup/{trigger}", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def retrieve_package(self, trigger: str, detail_level: str = "summary_and_state", output_format: str = "markdown") -> Dict[str, Any]:
        payload = {"trigger": trigger, "detail_level": detail_level, "output_format": output_format}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/retrieve", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def retrieve_prompt(self, prompt: str, detail_level: str = "summary_and_state", output_format: str = "prompt") -> Dict[str, Any]:
        payload = {"prompt": prompt, "detail_level": detail_level, "output_format": output_format}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/retrieve-prompt", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def search_contexts(self, query: str, limit: int = 10, search_mode: str = "hybrid") -> Dict[str, Any]:
        payload = {"query": query, "limit": limit, "search_mode": search_mode}
        r = httpx.post(f"{self.base_url}/api/v1/search", headers=self._headers(), json=payload, timeout=8.0)
        r.raise_for_status()
        return r.json()

    def list_triggers(self, search: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if search:
            params["search"] = search
        r = httpx.get(f"{self.base_url}/api/v1/triggers", headers=self._headers(), params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def register_trigger(self, trigger_word: str, context_id: str, is_primary: bool = False) -> Dict[str, Any]:
        payload = {"trigger_word": trigger_word, "context_id": context_id, "is_primary": is_primary}
        r = httpx.post(f"{self.base_url}/api/v1/triggers", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def rename_trigger(self, old_trigger: str, new_trigger: str) -> Dict[str, Any]:
        payload = {"new_trigger_word": new_trigger}
        r = httpx.patch(f"{self.base_url}/api/v1/triggers/{old_trigger}", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def remove_trigger(self, trigger_word: str) -> Dict[str, Any]:
        r = httpx.delete(f"{self.base_url}/api/v1/triggers/{trigger_word}", headers=self._headers(), timeout=6.0)
        r.raise_for_status()
        return r.json()

    def list_versions(self, context_id: str) -> List[Dict[str, Any]]:
        r = httpx.get(f"{self.base_url}/api/v1/contexts/{context_id}/versions", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def compare_versions(self, context_id: str, v1: int, v2: int) -> Dict[str, Any]:
        params = {"v1": v1, "v2": v2}
        r = httpx.get(f"{self.base_url}/api/v1/contexts/{context_id}/versions/compare/diff", headers=self._headers(), params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def restore_version(self, context_id: str, version_id: str, reason: str = "") -> Dict[str, Any]:
        payload = {"reason": reason}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/{context_id}/versions/restore/{version_id}", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def export_context(self, context_id: str, format: str = "json") -> Dict[str, Any]:
        params = {"format": format}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/{context_id}/export", headers=self._headers(), params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def import_context(self, data: Dict[str, Any], new_trigger_word: Optional[str] = None) -> Dict[str, Any]:
        payload = {"data": data, "new_trigger_word": new_trigger_word}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/import", headers=self._headers(), json=payload, timeout=6.0)
        r.raise_for_status()
        return r.json()

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        payload = {"text": text}
        r = httpx.post(f"{self.base_url}/api/v1/contexts/extract", headers=self._headers(), json=payload, timeout=25.0)
        r.raise_for_status()
        return r.json()

    def auto_create_from_chat(self, chat_text: str, custom_trigger: Optional[str] = None) -> Dict[str, Any]:
        payload = {"chat_text": chat_text}
        if custom_trigger:
            payload["custom_trigger"] = custom_trigger
        r = httpx.post(f"{self.base_url}/api/v1/contexts/auto-create-from-chat", headers=self._headers(), json=payload, timeout=25.0)
        r.raise_for_status()
        return r.json()

    def create_api_key(self) -> Dict[str, Any]:
        r = httpx.post(f"{self.base_url}/api/v1/auth/api-key", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def revoke_api_key(self) -> Dict[str, Any]:
        r = httpx.delete(f"{self.base_url}/api/v1/auth/api-key", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()

    def get_me(self) -> Dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/v1/auth/me", headers=self._headers(), timeout=5.0)
        r.raise_for_status()
        return r.json()
