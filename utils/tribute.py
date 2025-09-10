from config import TRIBUTE_REQUEST_PRICE



def is_unlimited(requests_left):
    return requests_left == -1


def can_use(requests_left):
    return is_unlimited(requests_left) or (requests_left >= TRIBUTE_REQUEST_PRICE)



