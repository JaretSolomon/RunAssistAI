from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests

from .config_loader import load_json_config


STRAVA_OAUTH_AUTHORIZE = "https://www.strava.com/oauth/authorize"
STRAVA_OAUTH_TOKEN = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


class StravaAPIError(RuntimeError):
    """
    Raised when Strava returns an error response.
    """


class StravaClient:
    """
    Minimal Strava API client that supports OAuth token exchange/refresh
    and fetching athlete activities.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        config = load_json_config("strava_config.json", "strava_config.example.json")

        def _clean(value: Any) -> Optional[str]:
            if value is None:
                return None
            text = str(value).strip()
            return text or None

        self.client_id = client_id or os.getenv("STRAVA_CLIENT_ID") or _clean(
            config.get("client_id")
        )
        self.client_secret = (
            client_secret
            or os.getenv("STRAVA_CLIENT_SECRET")
            or _clean(config.get("client_secret"))
        )
        self.redirect_uri = (
            redirect_uri
            or os.getenv("STRAVA_REDIRECT_URI")
            or _clean(config.get("redirect_uri"))
        )

    # ---------- configuration helpers ----------

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def _require_config(self) -> None:
        if not self.is_configured():
            raise RuntimeError(
                "Strava is not configured. Please set STRAVA_CLIENT_ID, "
                "STRAVA_CLIENT_SECRET, and STRAVA_REDIRECT_URI."
            )

    # ---------- OAuth helpers ----------

    def build_authorize_url(
        self,
        state: str,
        scope: str = "activity:read_all",
        approval_prompt: str = "auto",
    ) -> str:
        self._require_config()
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": state,
            "approval_prompt": approval_prompt,
        }
        return f"{STRAVA_OAUTH_AUTHORIZE}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        self._require_config()
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        return self._request_token(payload)

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        self._require_config()
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return self._request_token(payload)

    def _request_token(self, data: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(STRAVA_OAUTH_TOKEN, data=data, timeout=30)
        if resp.status_code != 200:
            raise StravaAPIError(
                f"Strava token request failed: {resp.status_code} {resp.text}"
            )
        return resp.json()

    # ---------- Activities ----------

    def list_activities(
        self,
        access_token: str,
        after: Optional[int] = None,
        per_page: int = 50,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if after is not None:
            params["after"] = after

        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            headers=headers,
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            raise StravaAPIError(
                f"Strava activities request failed: {resp.status_code} {resp.text}"
            )
        data = resp.json()
        if not isinstance(data, list):
            raise StravaAPIError("Unexpected Strava activities payload")
        return data

