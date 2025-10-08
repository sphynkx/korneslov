from db.tgpayments import get_user_amount, set_user_amount, set_user_amount
from config import TGPAYMENT_PROVIDERS, TGPAYMENT_REQUEST_PRICES


def get_provider_by_currency(currency: str):
    for provider in TGPAYMENT_PROVIDERS:
        if provider["currency"] == currency:
            return provider
    return None


def is_unlimited(requests_left):
    return requests_left == -1


def can_use(requests_left, level="light"):
    """
    Is enough credits for request with defined level.
    :param requests_left: int — user balance
    :param level: str — levels ("light", "smart", "hard")
    """
    price = TGPAYMENT_REQUEST_PRICES.get(level, 1)
    return is_unlimited(requests_left) or (requests_left >= price)


## Flush all flags, critical for payment menus
def reset_payment_state(state):
    print(f"DBG ResetState BEFOR: {state=}")
    for key in ["await_amount", "amount", "currency", "method", "direction"]:
        state.pop(key, None)
    print(f"DBG ResetState AFTA: {state=}")

