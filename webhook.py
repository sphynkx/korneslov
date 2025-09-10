import hmac
import hashlib
from flask import Flask, request, jsonify
from config import TRIBUTE_WEBHOOK_SECRET, TRIBUTE_REQUEST_PRICE
from db.tribute import add_tribute_payment, get_user_requests_left, set_user_requests_left


app = Flask(__name__)



def verify_signature(raw_body, signature):
    digest = hmac.new(TRIBUTE_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature or "")


@app.route("/tribute_webhook", methods=["POST"])
def tribute_webhook():
    signature = request.headers.get("trbt-signature", "")
    raw = request.get_data()
    if not verify_signature(raw, signature):
        return jsonify({"status": "invalid signature"}), 401

    json_data = request.json or {}
    payload = json_data.get("payload", {})
    telegram_id = payload.get("telegram_user_id") or payload.get("uid")
    amount = float(payload.get("amount", 0))
    currency = payload.get("currency", "RUB")
    status = payload.get("status", "success")
    external_id = payload.get("external_id", "")
    datetime_val = payload.get("datetime", "")
    raw_json = str(json_data)

    if not telegram_id or amount <= 0:
        return jsonify({"status": "ignored"}), 200

    ## Write payment to tribute
    add_tribute_payment(
        user_id=int(telegram_id),
        product_id='manual',  ## some identifier (??)
        amount=amount,
        currency=currency,
        status=status,
        external_id=external_id,
        datetime=datetime_val,
        raw_json=raw_json,
    )

    ## Calculate how mach request we may add for user when he has paid
    requests_to_add = int(amount // TRIBUTE_REQUEST_PRICE)

    ## Refresh user balance
    current_requests = get_user_requests_left(int(telegram_id))
    set_user_requests_left(int(telegram_id), current_requests + requests_to_add)

    return jsonify({
        "status": "ok",
        "telegram_id": telegram_id,
        "requests_added": requests_to_add
    }), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

