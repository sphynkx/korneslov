import os
from dotenv import load_dotenv

load_dotenv()

## Keys and tokens
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

## DB support
##DATABASE_FILE = os.getenv("DATABASE_FILE", "korneslov.db")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 3306)
DB_NAME = os.getenv("DB_NAME", "korneslov")
DB_USER = os.getenv("DB_USER", "korneslov")
DB_PASS = os.getenv("DB_PASS", "")

## Dev parameters
TESTMODE = os.getenv("TESTMODE", "False").lower() == "true"
USE_TRIBUTE = os.getenv("USE_TRIBUTE", "False").lower() == "true"

## Tribute support - will be DEPRECATED
TRIBUTE_WEBHOOK_SECRET = os.getenv("TRIBUTE_WEBHOOK_SECRET", "")
##TRIBUTE_PRODUCT_10_ID = os.getenv("TRIBUTE_PRODUCT_10_ID", "prod_10_requests")
##TRIBUTE_PRODUCT_10_URL = os.getenv("TRIBUTE_PRODUCT_10_URL", "")
##QUERIES_FOR_10 = int(os.getenv("QUERIES_FOR_10", "10"))
TRIBUTE_REQUEST_PRICE=int(os.getenv("TRIBUTE_REQUEST_PRICE", "10"))
TRIBUTE_PAYMENT_URL=os.getenv("TRIBUTE_PAYMENT_URL", "https://tribute.tg/pay/PAYMENT_ID")

## Telegram Bot Payment
TGPAYMENT_PROVIDER_TOKEN = os.getenv("TGPAYMENT_PROVIDER_TOKEN", "TEST")
TGPAYMENT_PROVIDER_CURRENCY = os.getenv("TGPAYMENT_PROVIDER_CURRENCY", "RUB")
TGPAYMENT_AMOUNT = int(os.getenv("TGPAYMENT_AMOUNT", "1000"))
TGPAYMENT_PHOTO = os.getenv("TGPAYMENT_PHOTO", "")


## OpenAI params
OPENAI_MODEL = "gpt-5"
OPENAI_MODEL_PARAMS = {
    "gpt-4o-mini": {"max_tokens": 3000, "temperature": 0.7},
    "gpt-4o": {"max_tokens": 3000, "temperature": 0.7},
    "gpt-5": {},
}
def get_model_and_params():
    from config import OPENAI_MODEL, OPENAI_MODEL_PARAMS
    return OPENAI_MODEL, OPENAI_MODEL_PARAMS.get(OPENAI_MODEL, {})