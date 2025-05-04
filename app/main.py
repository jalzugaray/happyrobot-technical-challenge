import os, httpx
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from .security import verify_api_key

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

app = FastAPI(title="Simple Dedup Router")

@app.post("/process-load", dependencies=[Depends(verify_api_key)])
async def process_load(call: CallSchema):
    payload = call.model_dump()

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
