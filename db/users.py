from db import execute, fetchone, fetchall
import datetime


## Get user by user_id
async def get_user(user_id):
    return await fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))


## Add new user
## Strange bug.. w/o debugs it was not add new user sometimes!! Need to monitor..
async def add_user(user_id, firstname, lastname, username, lang, is_bot):
    print(f"DBG: add_user(): {user_id=}, {firstname=}, {lastname=}, {username=}, {lang=}, {is_bot=}")
    now = datetime.datetime.now()
    try:
        res = await execute(
            "INSERT INTO users (user_id, firstname, lastname, username, lang, is_bot, last_seen) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (user_id, firstname, lastname, username, lang, is_bot, now)
        )
        print(f"DBG: add_user() result: {res}")
        return res
    except Exception as e:
        print(f"ERROR in add_user: {e}")
        raise


## Update user data (firstname, lastname, username, lang, is_bot, last_seen)
async def update_user(user_id, firstname, lastname, username, lang, is_bot):
    print(f"DBG: update_user(): {user_id=}, {firstname=}, {lastname=}, {username=}, {lang=}, {is_bot=}")
    now = datetime.datetime.now()
    await execute(
        "UPDATE users SET firstname=%s, lastname=%s, username=%s, lang=%s, is_bot=%s, last_seen=%s WHERE user_id=%s",
        (firstname, lastname, username, lang, is_bot, now, user_id)
    )


## Create or update user then he enters (upsert)
async def upsert_user(user_id, firstname, lastname, username, lang, is_bot):
    print(f"DBG upsert_user(): {user_id=}, {firstname=}, {lastname=}, {username=}, {lang=}, {is_bot=}")
    user = await get_user(user_id)
    print(f"upsert_user()->get_user(): {user=}")
    if user:
        await update_user(user_id, firstname, lastname, username, lang, is_bot)
    else:
        await add_user(user_id, firstname, lastname, username, lang, is_bot)


