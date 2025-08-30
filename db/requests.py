from db import execute, fetchone, fetchall
import datetime
import json


## Add new request (returns id)
async def add_request(user_id, user_state, request, status_oai=None, status_tg=None):
    now = datetime.datetime.now()
    return await execute(
        "INSERT INTO requests (user_id, user_state, datetime_request, request, status_oai, status_tg) VALUES (%s,%s,%s,%s,%s,%s)",
        (user_id, json.dumps(user_state), now, request, status_oai, status_tg)
    )


## Updete response time and delay
async def update_request_response(request_id, status_oai, status_tg):
    now = datetime.datetime.now()
    req = await fetchone("SELECT datetime_request FROM requests WHERE id=%s", (request_id,))
    delay = None
    if req and req["datetime_request"]:
        delay = (now - req["datetime_request"]).total_seconds()
    await execute(
        "UPDATE requests SET datetime_response=%s, delay=%s, status_oai=%s, status_tg=%s WHERE id=%s",
        (now, delay, status_oai, status_tg, request_id)
    )


