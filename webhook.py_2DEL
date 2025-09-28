import hmac
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime
import json
from quart import Quart, request, jsonify
from config import TRIBUTE_WEBHOOK_SECRET, TRIBUTE_REQUEST_PRICE
from db.tribute import (
    add_tribute_payment,
    get_user_amount_and_external_id,
    atomic_update_user_amount_and_external_id,
)
import asyncio

app = Quart(__name__)

def verify_signature(raw_body: bytes, signature: str) -> bool:
    digest = hmac.new(TRIBUTE_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature or "")

def normalize_datetime(dt_str: str) -> str | None:
    """Reformat ISO8601to 'YYYY-MM-DD HH:MM:SS'."""
    if not dt_str:
        return None
    try:
        s = dt_str.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if "T" in s and "." in s:
            date_part, rest = s.split("T", 1)
            time_part = rest
            tz_sep = max(time_part.rfind("+"), time_part.rfind("-"))
            if tz_sep > 0:
                core, tz = time_part[:tz_sep], time_part[tz_sep:]
            else:
                core, tz = time_part, ""
            if "." in core:
                core = core.split(".", 1)[0]
            s = f"{date_part}T{core}{tz}"
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

@app.route("/", methods=["GET"])
async def index():
    return "Webhook server is alive", 200

@app.route("/tribute_webhook", methods=["POST"])
async def tribute_webhook():
    # DBG section
    raw_text = await request.get_data(as_text=True)
    headers = dict(request.headers)
    print("=== Tribute webhook ===")
    print("Headers:", headers)
    print("Raw body:", raw_text)
    print("=======================")

    signature = request.headers.get("Trbt-Signature", "")
    raw = await request.get_data()
    if not verify_signature(raw, signature):
        return jsonify({"status": "invalid signature"}), 401

    # JSON and payload
    json_data = await request.get_json(force=True)
    payload = json_data.get("payload", {}) or {}

    telegram_id = payload.get("telegram_user_id") or payload.get("uid")
    amount_raw = payload.get("amount", "0")
    currency = payload.get("currency", "RUB")
    status = (payload.get("status") or "").lower() or "success"
    external_id = payload.get("external_id", "") or payload.get("id", "")
    product_id = payload.get("product_id") or json_data.get("product_id") or "manual"
    datetime_iso = payload.get("datetime", "") or payload.get("created_at", "")

    # Common validation
    if not telegram_id:
        return jsonify({"status": "ignored", "reason": "no user id"}), 200

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        amount = Decimal("0")

    if amount <= 0:
        return jsonify({"status": "ignored", "reason": "non-positive amount"}), 200

    # Normalize date
    datetime_val = normalize_datetime(datetime_iso)
    if datetime_iso and not datetime_val:
        print(f"[warn] failed to parse datetime: {datetime_iso}")

    # Write payload to DB - always!! both success and unsuccess
    await add_tribute_payment(
        user_id=int(telegram_id),
        product_id=str(product_id),
        amount=amount,
        currency=str(currency),
        status=str(status),
        external_id=str(external_id),
        datetime_val=datetime_val,  # 'YYYY-MM-DD HH:MM:SS' or None
        raw_json=raw_text,
    )

    # Accrual - for success only, ATOMIC!
    success_statuses = {"success", "succeeded", "paid", "completed"}
    requests_added = 0
    try:
        unit_price = Decimal(str(TRIBUTE_REQUEST_PRICE))
    except (InvalidOperation, TypeError):
        unit_price = Decimal("1")

    if status in success_statuses and unit_price > 0:
        requests_added = int(amount // unit_price)
        if requests_added > 0:
            updated = await atomic_update_user_amount_and_external_id(
                int(telegram_id), requests_added, str(external_id)
            )
            if not updated:
                print(f"[info] Payment {external_id} for user {telegram_id} already processed, skipping accrual.")

    return jsonify(
        {
            "status": "ok",
            "telegram_id": str(telegram_id),
            "requests_added": requests_added,
            "product_id": str(product_id),
            "external_id": str(external_id),
        }
    ), 200

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

