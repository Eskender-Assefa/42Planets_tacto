"""Minimal Supabase (PostgREST) client for the runner's write path.

Uses the service-role key from SUPABASE_SERVICE_ROLE_KEY - server side only, never ship it to the
dashboard. Every call has a timeout and raises DBError on any failure, so callers can decide
whether to fall back (e.g. local SQLite) or refuse to send the move.
"""

import logging
import os
from collections.abc import Mapping, Sequence

import httpx

from .types import AuditLogRow, CaseRow, SupplierRow

log = logging.getLogger("hollerau.db")

# A write blocks the move it precedes: keep it far below the arena's 60 s per-message limit.
TIMEOUT_S = 8.0

# JSON values PostgREST returns; rows are dicts of these.
type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]
type Row = dict[str, JSONValue]


class DBError(Exception):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message if status is None else f"HTTP {status}: {message}")
        self.status = status


class SupabaseDB:
    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
        *,
        timeout: float = TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise DBError("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (starter-kit/.env)")
        self.http = httpx.Client(
            base_url=f"{url}/rest/v1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self.http.close()

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: Mapping[str, str] | None = None,
        body: Sequence[Mapping[str, object]] | Mapping[str, object] | None = None,
        prefer: str | None = None,
    ) -> list[Row]:
        headers = {"Prefer": prefer} if prefer else {}
        try:
            r = self.http.request(method, f"/{table}", params=params, json=body, headers=headers)
        except httpx.HTTPError as e:  # timeouts, DNS, connection resets
            log.error("supabase %s %s failed: %s", method, table, e)
            raise DBError(f"{type(e).__name__}: {e}") from e
        if r.status_code >= 400:
            try:
                err = r.json()
                detail = str(err.get("message", r.text)) if isinstance(err, dict) else r.text
            except ValueError:
                detail = r.text
            raise DBError(f"{method} {table}: {detail}", r.status_code)
        if not r.content:
            return []
        data = r.json()
        return data if isinstance(data, list) else [data]

    def upsert_suppliers(self, rows: Sequence[SupplierRow]) -> list[Row]:
        return self._request("POST", "suppliers", body=rows, prefer="resolution=merge-duplicates,return=representation")

    def upsert_case(self, row: CaseRow) -> Row:
        out = self._request("POST", "cases", body=row, prefer="resolution=merge-duplicates,return=representation")
        return out[0]

    def insert_audit(self, row: AuditLogRow) -> Row:
        """Insert one move's audit row. Raises DBError (409) if this move was already logged."""
        out = self._request("POST", "audit_logs", body=row, prefer="return=representation")
        if not out:
            raise DBError("audit insert returned no row - write not verified")
        return out[0]

    def select(self, table: str, **filters: str) -> list[Row]:
        """`filters` are PostgREST filters, e.g. session_id="eq.sim1"."""
        return self._request("GET", table, params={"select": "*", **filters})

    def delete(self, table: str, **filters: str) -> list[Row]:
        if not filters:
            raise DBError("refusing to delete without a filter")
        return self._request("DELETE", table, params=filters, prefer="return=representation")
