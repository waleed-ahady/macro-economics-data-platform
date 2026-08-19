import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WorldBankApiError(RuntimeError):
    pass


class WorldBankClient:
    """Small client for the World Bank Indicators API v2."""

    def __init__(
        self,
        base_url: str = "https://api.worldbank.org/v2",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def __enter__(self) -> "WorldBankClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request_params = {"format": "json", **params}
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self.client.get(url, params=request_params)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(0.5 * (2**attempt))
                    continue
                if isinstance(exc, httpx.HTTPStatusError):
                    message = exc.response.text[:500]
                    raise WorldBankApiError(
                        f"World Bank request failed ({exc.response.status_code}): {message}"
                    ) from exc
                raise WorldBankApiError("World Bank request failed") from exc
        raise WorldBankApiError("World Bank request failed after retries") from last_error

    def get_indicator_observations(
        self,
        indicator_id: str,
        country_codes: list[str],
        *,
        start_year: int,
        end_year: int,
    ) -> list[dict[str, Any]]:
        if not country_codes:
            return []

        country_path = ";".join(country_codes)
        page = 1
        records: list[dict[str, Any]] = []
        while True:
            payload = self._get(
                f"country/{country_path}/indicator/{indicator_id}",
                {
                    "date": f"{start_year}:{end_year}",
                    "per_page": 20000,
                    "page": page,
                },
            )
            if not isinstance(payload, list) or len(payload) < 2:
                raise WorldBankApiError(f"Unexpected response for indicator {indicator_id}")
            metadata = payload[0] or {}
            page_records = payload[1] or []
            records.extend(dict(item) for item in page_records)
            pages = int(metadata.get("pages") or 1)
            if page >= pages:
                break
            page += 1
        return records


def parse_world_bank_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
