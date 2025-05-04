# app/security.py
import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY")           # must be set in Render (or locally)

if API_KEY is None:
    raise RuntimeError("API_KEY env‑var missing")

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")