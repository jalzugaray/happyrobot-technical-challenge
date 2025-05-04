import os, httpx
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from .security import verify_api_key
from .fmcsa_verification import check_mc_active
import pandas as pd

app = FastAPI(title="Simple Router")

WF2_URL  = os.getenv("WF2_URL")
WF2_KEY  = os.getenv("WF2_API_KEY")
if not WF2_URL or not WF2_KEY:
    raise RuntimeError("WF2_URL and WF2_API_KEY env‑vars are required")

# in‑memory list of new‑calls we already dialed
new_calls_list: list[dict] = []
voicemail_retry: list[dict] = []

class CallSchema(BaseModel):
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
    payload = call.model_dump()

    # fmcsa validation
    if call.validate_carrier == "yes":
        result = await check_mc_active(call.carrier_mc_number)
        if result["abort"]:
            return {"status": "carrier_validation_failed",
                    "reason": result["reason"]}

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
    
    elif call.type_of_call == "reschedule_call":
        # forward to workflow 2
        async with httpx.AsyncClient() as client:
            await client.post(
                WF2_URL,
                json=payload,
                headers={"X-API-Key": WF2_KEY}
            )
    
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
    carrier_phone: str
    carrier_name: str
    call_duration_sec: str
    outcome: str
    sentiment: str
    rate_usd: str | None = None
    origin: str
    destination: str
    miles: str

# global in‑memory DataFrame to accumulate call analytics
analytics_df = pd.DataFrame(columns=CallAnalytics.model_fields.keys())

@app.post("/process-call", dependencies=[Depends(verify_api_key)])
async def process_call(call: CallAnalytics):
    global analytics_df

    row = call.model_dump()
    row["call_duration_sec"] = int(row["call_duration_sec"])
    row["rate_usd"] = float(row["rate_usd"]) if row["rate_usd"] not in (None, "", "N/A") else pd.NA
    row["miles"] = int(row["miles"])
    
    analytics_df.loc[len(analytics_df)] = row

    return {"status": "logged"}