import asyncio
import httpx
import json
import time

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_RETRIES = 2
BACKOFF_SECONDS = 0.5

# data is the json response parsed into a dict
# path could be a string like "team.stats.assists"
def field_exists(data: dict, path: str) -> bool:
    for key in path.split("."):
        if key not in data:
            return False
        # if key exists, move one level deeper
        data = data[key]
    return True


# check is an APICheck object
async def run_check(check):
    response = None
    latency_ms = None
    last_error = None

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        # wrap http requests in a retry loop
        for attempt in range(MAX_RETRIES + 1):
            start_time = time.perf_counter()
            try:
                response = await client.request(check.method, str(check.url))
                # time.perf_counter() for higher precision timing for latency
                latency_ms = (time.perf_counter() - start_time) * 1000
                break
            except httpx.RequestError as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000
                last_error = str(exc)
                if attempt == MAX_RETRIES:
                    return {
                        "status": "FAIL",
                        "missing_fields": [],
                        "error": f"Request failed after {MAX_RETRIES + 1} attempts: {last_error}",
                        "status_code": None,
                        "latency_ms": latency_ms,
                    }
                await asyncio.sleep(BACKOFF_SECONDS * (2 ** attempt))
    try:
        data = response.json()
    except json.JSONDecodeError:
        return {
            "status": "FAIL",
            "missing_fields": [],
            "error": "Response is not valid JSON",
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        }

    # record any missing fields
    missing = []
    for field in check.required_fields:
        if not field_exists(data, field):
            missing.append(field)

    status = "PASS"
    if missing:
        status = "FAIL"
    if hasattr(check, "expected_status_code") and response.status_code != check.expected_status_code:
        status = "FAIL"

    # failure if latency exceeds threshold
    if hasattr(check, "latency_threshold_ms") and check.latency_threshold_ms:
        if latency_ms > check.latency_threshold_ms:
            status = "FAIL"

    return {
        "status": status,
        "missing_fields": missing,
        "status_code": response.status_code,
        "latency_ms": latency_ms,
        "error": None,
    }