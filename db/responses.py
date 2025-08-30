from db import execute, fetchone, fetchall


## Store OpeAI responses
async def add_response(request_id, data):
    return await execute(
        "INSERT INTO responses (request_id, data) VALUES (%s,%s)",
        (request_id, data)
    )


## Receive response by request_id
async def get_response(request_id):
    return await fetchone("SELECT * FROM responses WHERE request_id=%s", (request_id,))

