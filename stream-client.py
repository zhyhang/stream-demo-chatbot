"""Generic client for interacting with a Streamlit app
running on Streamlit Community Cloud.

This client is designed to talk to the existing app at
https://yanghuangshi.streamlit.app and can be reused for
future query-parameter based APIs you add to the app.

Current capabilities:
- Perform a health check using `?health=check`.
- Provide a generic `call_raw` and `call_api` method that can
  be used once additional APIs are exposed via query params.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class ResponseInfo:
    """Structured information about a single HTTP call.

    Attributes:
        ok: Whether the request was successful.
        status_code: HTTP status code, if available.
        elapsed: Time taken for the request, in seconds.
        data: Parsed JSON data or raw text, if any.
        error: String description of an error, if any.
    """

    ok: bool
    status_code: Optional[int]
    elapsed: Optional[float]
    data: Any
    error: Optional[str]


class StreamlitBackendClient:
    """Client for a Streamlit app deployed on Streamlit Cloud.

    The client assumes that the app exposes functionality via
    query parameters on the root path, e.g.:
        - ?health=check
        - ?api=chat&prompt=...
    """

    def __init__(
        self,
        base_url: str = "https://yanghuangshi.streamlit.app",
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Low-level GET request to the app root with query params."""
        url = f"{self.base_url}/"
        return self.session.get(url, params=params, timeout=self.timeout)

    def call_raw(self, params: Dict[str, Any]) -> ResponseInfo:
        """Generic call with arbitrary query parameters.

        This is the lowest-level entry point for interacting
        with the Streamlit app via query parameters. It is
        suitable both for the existing health check and for
        future APIs you may add.
        """
        status_code: Optional[int] = None
        elapsed: Optional[float] = None
        data: Any = None
        error: Optional[str] = None
        ok = False

        try:
            resp = self._get(params=params)
            status_code = resp.status_code
            elapsed = resp.elapsed.total_seconds()
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception:
                # Fallback to raw text if response is not valid JSON
                data = resp.text
            ok = True
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        return ResponseInfo(
            ok=ok,
            status_code=status_code,
            elapsed=elapsed,
            data=data,
            error=error,
        )

    def call_api(self, api_name: str, **params: Any) -> ResponseInfo:
        """High-level API call using the `?api=<name>` convention.

        This is intended for future use when the Streamlit app
        implements endpoints such as `?api=chat&...`.
        """
        query: Dict[str, Any] = {"api": api_name}
        query.update(params)
        return self.call_raw(query)

    def exec_command(self, command: str) -> ResponseInfo:
        """Execute a shell command via the `?api=exec` endpoint.

        The backend Streamlit app is expected to implement a handler for
        `?api=exec&command=<...>` that executes the command and returns
        a structured JSON response, for example::

            {"ok": true, "result": "...", "return_code": 0}
        """
        return self.call_api("exec", command=command)

    def health_check(self) -> ResponseInfo:
        """Call the existing `?health=check` endpoint."""
        return self.call_raw({"health": "check"})

    def is_healthy(self) -> bool:
        """Return True if the app appears reachable and healthy.

        On Streamlit Community Cloud, the HTTP response body for
        `?health=check` is typically the HTML shell of the app, while
        the JSON rendered via `st.json` is delivered over WebSockets
        to a browser client. Therefore we primarily rely on HTTP
        status, and treat JSON with `status="healthy"` as a special
        case (useful in local environments).
        """
        info = self.health_check()
        if not info.ok:
            return False
        # Local / non-Cloud environments may return JSON directly.
        if isinstance(info.data, dict) and info.data.get("status") == "healthy":
            return True
        # Fallback: consider a successful HTTP status as healthy.
        return info.status_code is not None and 200 <= info.status_code < 300


def main() -> None:
    """Simple CLI entry point for manual testing.

    Usage examples (from your local environment):
        python stream-client.py --health
        python stream-client.py --exec "ls -la"
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Client for interacting with a Streamlit app deployed "
            "on Streamlit Community Cloud."
        )
    )
    parser.add_argument(
        "--base-url",
        default="https://yanghuangshi.streamlit.app",
        help="Base URL of the Streamlit app (default: %(default)s)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Perform a health check and print the result.",
    )
    parser.add_argument(
        "--exec",
        dest="exec_cmd",
        help=(
            "Execute a shell command via the ?api=exec endpoint "
            "(backend must support this API)."
        ),
    )

    args = parser.parse_args()

    client = StreamlitBackendClient(base_url=args.base_url)

    if args.exec_cmd:
        info = client.exec_command(args.exec_cmd)
        print("Exec response:", info)
    else:
        # Default action: run or explicitly request a health check
        info = client.health_check()
        print("Health check:", info)
        print("Is healthy:", client.is_healthy())


if __name__ == "__main__":
    main()

