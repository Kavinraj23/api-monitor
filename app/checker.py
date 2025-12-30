import httpx
import json
import time

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
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        response = await client.get(str(check.url))  # ensure httpx gets a plain string URL
        latency_ms = (time.time() - start_time) * 1000
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "status": "FAIL",
                "missing_fields": [],
                "error": "Response is not valid JSON",
                "status_code": response.status_code,
                "latency_ms": latency_ms
            }

    # record any missing fields
    missing = []
    for field in check.required_fields:
        if not field_exists(data, field):
            missing.append(field)

    status = "PASS" if not missing else "FAIL"

    if hasattr(check, "expected_status_code") and response.status_code != check.expected_status_code:
        status = "FAIL"

    # failure if latency exceeds threshold
    if hasattr(check, "latency_threshold_ms") and check.latency_threshold_ms:
        if latency_ms > check.latency_threshold_ms:
            status = "FAIL"

    return {
        "status": "PASS" if not missing else "FAIL",
        "missing_fields": missing,
        "status_code": response.status_code,
        "latency_ms": latency_ms
    }