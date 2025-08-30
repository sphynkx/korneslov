from db import execute, fetchone, fetchall
import datetime
## Some dummy now.. Tribute will implemented in future.


## Add record
async def add_tribute(user_id, tribute_data):
    now = datetime.datetime.now()
    return await execute(
        "INSERT INTO tribute (user_id, tribute_data, datetime) VALUES (%s,%s,%s)",
        (user_id, tribute_data, now)
    )


## Get all tributes for user
async def get_tributes(user_id):
    return await fetchall("SELECT * FROM tribute WHERE user_id=%s", (user_id,))

