PI_CHAR = "π"
LEGACY_PI_TOKEN = "pi"


def normalize_pi_token(token):
    token = str(token or "")
    if token == LEGACY_PI_TOKEN:
        return PI_CHAR
    return token


def normalize_expression(text):
    return str(text or "").replace(PI_CHAR, LEGACY_PI_TOKEN)
