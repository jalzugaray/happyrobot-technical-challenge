import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise RuntimeError("API_KEY environment variable not set")

def verify_api_key(authorization: str = Header(...)):
    """Check for Authorization: Bearer <API_KEY>"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Missing Bearer token")
    
    token = authorization.replace("Bearer ", "", 1)
    if token != API_KEY:
        raise HTTPException(401, detail="Invalid API key")
