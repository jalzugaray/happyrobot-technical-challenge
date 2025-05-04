"""
FMCSA Carrier Verification Module

This module provides functionality to verify carrier MC numbers through the FMCSA API.
It checks if a carrier is active and authorized to operate.
"""

import os, httpx

# FMCSA API configuration
FMC_WEB_KEY = os.getenv("FMC_WEB_KEY")
BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number/{}"

if not FMC_WEB_KEY:
    raise RuntimeError("FMC_WEB_KEY env‑var missing")

async def check_mc_active(mc_number: str) -> dict:
    """
    Verify if a carrier's MC number is active and authorized to operate.
    
    This function queries the FMCSA API to check the status of a carrier's MC number.
    It returns a dictionary indicating whether the carrier is valid and active.
    
    Args:
        mc_number: The carrier's MC number to verify
        
    Returns:
        dict: A dictionary with the following structure:
            - If carrier is invalid/inactive:
                {"abort": True, "reason": "error message"}
            - If carrier is valid and active:
                {"abort": False}
                
    Raises:
        RuntimeError: If FMC_WEB_KEY environment variable is not set
        httpx.RequestError: If there's an error communicating with the FMCSA API
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
