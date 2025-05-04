"""
Main FastAPI application for the Happy Robot Technical Challenge.

This module implements a call processing and analytics system with the following features:
- Call deduplication and routing
- Carrier validation through FMCSA
- Call analytics tracking
- Real-time dashboard visualization

The application uses in-memory storage for call tracking and analytics.
"""

import os, httpx
from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from .security import verify_api_key
from .fmcsa_verification import check_mc_active
import pandas as pd

app = FastAPI(title="Simple Router")

# Environment variables for external services
WF2_URL  = os.getenv("WF2_URL")
WF2_KEY  = os.getenv("WF2_API_KEY")
if not WF2_URL or not WF2_KEY:
    raise RuntimeError("WF2_URL and WF2_API_KEY env‑vars are required")

# In-memory storage for call tracking
new_calls_list: list[dict] = []  # Tracks new calls to prevent duplicates
voicemail_retry: list[dict] = []  # Tracks voicemail retry attempts

class CallSchema(BaseModel):
    """Schema for incoming load call data."""
    origin: str
    destination: str
    pickup_datetime: str
    delivery_datetime: str
    equipment_type: str
    loadboard_rate: str
    notes: str
    weight: str
    commodity_type: str
    num_of_pieces: str
    miles: str
    dimensions: str
    carrier_name: str
    carrier_phone: str
    carrier_mc_number: str
    type_of_call: str
    validate_carrier: str

@app.post("/process-load", dependencies=[Depends(verify_api_key)])
async def process_load(call: CallSchema):
    """
    Process a new load call with deduplication and carrier validation.
    
    Args:
        call: Call data including carrier and load information
        
    Returns:
        dict: Processing status and any relevant messages
    """
    payload = call.model_dump()

    # fmcsa validation
    if call.validate_carrier == "yes":
        result = await check_mc_active(call.carrier_mc_number)
        if result["abort"]:
            return {"status": "carrier_validation_failed",
                    "reason": result["reason"]}

    # If the call is new, we first check we havent done it yet
    if call.type_of_call == "new_call":
        if payload in new_calls_list:
            return {"status": "duplicate_skipped"}
        new_calls_list.append(payload)

        # forward to workflow 2
        async with httpx.AsyncClient() as client:
            await client.post(
                WF2_URL,
                json=payload,
                headers={"X-API-Key": WF2_KEY}
            )
    
    # A call can be rescheduled as many times as the carrier wnats
    elif call.type_of_call == "reschedule_call":
        # forward to workflow 2
        async with httpx.AsyncClient() as client:
            await client.post(
                WF2_URL,
                json=payload,
                headers={"X-API-Key": WF2_KEY}
            )
    
    # If call went straight to voicemail it will only retry for 3 times
    elif call.type_of_call == "voicemail_retry":
        retry_count = voicemail_retry.count(payload)
        if retry_count == 3:
            return {"status": "retry_limit_reached"}
        voicemail_retry.append(payload)

        # forward to workflow 2
        async with httpx.AsyncClient() as client:
            await client.post(
                WF2_URL,
                json=payload,
                headers={"X-API-Key": WF2_KEY}
            )

    return {"status": "forwarded"}

class CallAnalytics(BaseModel):
    """Schema for call analytics data."""
    carrier_phone: str
    carrier_name: str
    call_duration_sec: str
    outcome: str
    sentiment: str
    rate_usd: str | None = None
    origin: str
    destination: str
    miles: str

# Global in-memory DataFrame to accumulate call analytics
analytics_df = pd.DataFrame(columns=CallAnalytics.model_fields.keys())

@app.post("/process-call", dependencies=[Depends(verify_api_key)])
async def process_call(call: CallAnalytics):
    """
    Process and store call analytics data.
    
    Args:
        call: Analytics data for a completed call
        
    Returns:
        dict: Processing status
    """
    global analytics_df

    row = call.model_dump()
    row["call_duration_sec"] = int(row["call_duration_sec"])
    row["rate_usd"] = float(row["rate_usd"]) if row["rate_usd"] not in (None, "", "N/A") else pd.NA
    row["miles"] = int(row["miles"])
    
    analytics_df.loc[len(analytics_df)] = row

    return {"status": "logged"}

def compute_metrics():
    """
    Compute key metrics from the analytics data.
    
    Returns:
        dict: Metrics including acceptance rate, connection rate, and rate statistics
    """
    if analytics_df.empty:
        return dict(acceptance_rate=0, connection_rate=0,
                    avg_rate_usd=0, total_rate_usd=0)

    connected_df = analytics_df[analytics_df["outcome"] != "voicemail"]
    acceptance_rate = (
        len(connected_df[connected_df["outcome"] == "accept"]) /
        len(connected_df)
    ) if len(connected_df) else 0

    connection_rate = (
        len(connected_df) / len(analytics_df)
    )

    rate_series = connected_df[connected_df["outcome"] == "accept"]["rate_usd"].dropna().astype(float)
    avg_rate = rate_series.mean() if not rate_series.empty else 0
    total_rate = rate_series.sum() if not rate_series.empty else 0

    return dict(
        acceptance_rate=acceptance_rate,
        connection_rate=connection_rate,
        avg_rate_usd=avg_rate,
        total_rate_usd=total_rate,
    )

@app.get("/metrics", dependencies=[Depends(verify_api_key)])
def get_metrics():
    """Return computed metrics in JSON format."""
    return compute_metrics()

templates = Jinja2Templates(directory="app/templates")
DASHBOARD_TOKEN = os.getenv("DASHBOARD_API_KEY", "test")   # default for dev
# ---------- Simple HTML dashboard ---------------------------
@app.get("/dashboard", dependencies=[Depends(verify_api_key)])
def dashboard(request: Request):
    """Serve the analytics dashboard UI."""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "dash_token": DASHBOARD_TOKEN}
    )