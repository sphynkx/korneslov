from config import TGPAYMENT_PROVIDERS


def get_provider_by_currency(currency: str):
    for provider in TGPAYMENT_PROVIDERS:
        if provider["currency"] == currency:
            return provider
    return None
