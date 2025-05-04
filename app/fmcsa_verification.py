import os, httpx

FMC_WEB_KEY = os.getenv("FMC_WEB_KEY")
BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{}"

if not FMC_WEB_KEY:
    raise RuntimeError("FMC_WEB_KEY env‑var missing")

async def check_mc_active(mc_number: str) -> dict:
    """
    Returns {"abort": True, "reason": "..."}  when MC is invalid / inactive,
            {"abort": False}                  when everything is OK.
    """
    url = BASE.format(mc_number)
    params = {"webKey": FMC_WEB_KEY}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)

    if r.status_code != 200:
        return {"abort": True, "reason": "Invalid MC number — no carrier found"}

    data = r.json()
    if not isinstance(data, dict) or not data:
        return {"abort": True, "reason": "Invalid MC number — empty response"}

    if data.get("allowToOperate") != "Y":
        status = data.get("status")
        return {"abort": True,
                "reason": f"Carrier inactive — status={status}"}

    return {"abort": False}
