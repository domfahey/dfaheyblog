import json
import logging

import requests
from django.conf import settings
from sentry_sdk import capture_exception


def using_mailing_list():
    return settings.CONVERT_KIT_API_KEY and settings.CONVERT_KIT_FORM_ID


def subscribe_to_mailing_list(email_address):
    if not using_mailing_list():
        return
    try:
        add_subscriber_url = f"https://api.convertkit.com/v3/forms/{settings.CONVERT_KIT_FORM_ID}/subscribe"
        parameters = {
            "api_key": settings.CONVERT_KIT_API_KEY,
            "email": email_address,
            "tags": [],
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(add_subscriber_url, data=json.dumps(parameters), headers=headers)
        if response.status_code != 200:
            logging.error(f"Unable to add {email_address} to mailing list: {response.text}")
    except Exception as e:
        # capture errors but don't crash
        capture_exception(e)
