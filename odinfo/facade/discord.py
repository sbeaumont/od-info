import requests
from odinfo.config import discord_webhook


def send_to_webhook(message):
    content = {
        'username': 'OD Info',
        'content': message
    }
    return requests.post(discord_webhook, json=content)
