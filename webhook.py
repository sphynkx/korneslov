import hmac
import hashlib
from flask import Flask, request, jsonify
from config import TRIBUTE_WEBHOOK_SECRET, TRIBUTE_PRODUCT_10_ID, QUERIES_FOR_10
from db import add_balance

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

    ## Simple parser - find telegram_id and product_id
    payload = json_data.get("payload", {})
    product_id = payload.get("product_id")
    telegram_id = payload.get("telegram_user_id") or payload.get("uid")

    if not (product_id and telegram_id):
        return jsonify({"status": "ignored"}), 200

    if product_id == TRIBUTE_PRODUCT_10_ID:
        add_balance(int(telegram_id), QUERIES_FOR_10)
        return jsonify({"status": "ok", "telegram_id": telegram_id, "queries_added": QUERIES_FOR_10}), 200

    return jsonify({"status": "unknown product"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)