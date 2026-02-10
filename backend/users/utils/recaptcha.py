
import requests
from django.conf import settings

def verify_recaptcha(token, action):
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": settings.RECAPTCHA_SECRET_KEY,
            "response": token,
        }
    ).json()

    return (
        response.get("success") and
        response.get("action") == action and
        response.get("score", 0) >= settings.RECAPTCHA_SCORE_THRESHOLD
    )
