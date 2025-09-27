## User-state: user_id -> dict
## Store current method, direction, level and language for separate user.
user_state = {}

def get_user_state(user_id):
    default = {
        "method": "korneslov",
        "direction": "masoret",
        "level": "hard",
        "lang": "ru",
        "currency": "UAH"
    }
    if user_id not in user_state:
        user_state[user_id] = default.copy()
    return user_state[user_id]
