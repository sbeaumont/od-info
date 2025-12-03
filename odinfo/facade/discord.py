import requests
from odinfo.config import get_config


def send_to_webhook(message):
    content = {
        'username': 'OD Info',
        'content': message
    }
    return requests.post(get_config().discord_webhook, json=content)
