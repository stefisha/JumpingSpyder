"""Bounded JSON transport. Retry idempotent reads; never blindly replay message sends."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    pass


class JsonHTTP:
    def __init__(self, timeout=20, attempts=3, opener=urlopen, sleep=time.sleep):
        self.timeout, self.attempts, self.opener, self.sleep = timeout, attempts, opener, sleep

    def request(self, method, url, headers=None, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        request = Request(
            url,
            data=payload,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        attempts = self.attempts if method == "GET" else 1
        for attempt in range(attempts):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ProviderError("Provider response exceeds size limit")
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ProviderError("Provider returned an unexpected JSON shape")
                return value
            except HTTPError as error:
                retryable = error.code in (429, 500, 502, 503, 504)
                if retryable and attempt + 1 < attempts:
                    delay = error.headers.get("Retry-After", "") if error.headers else ""
                    self.sleep(min(float(delay), 60) if delay.isdigit() else 2**attempt)
                    continue
                raise ProviderError(f"Provider HTTP {error.code}") from None
            except (URLError, TimeoutError, OSError):
                if attempt + 1 < attempts:
                    self.sleep(2**attempt)
                    continue
                raise ProviderError("Provider connection failed") from None
            except (ValueError, UnicodeError):
                raise ProviderError("Provider returned invalid JSON") from None
        raise ProviderError("Provider request failed")
