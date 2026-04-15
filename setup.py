"""Interactive setup script for OD Info.

Walks the user through configuring secret.txt and users.json
after a fresh install.
"""

import json
import os
import secrets
import string

INSTANCE_DIR = './instance'
SECRET_FILE = f'{INSTANCE_DIR}/secret.txt'
USERS_FILE = f'{INSTANCE_DIR}/users.json'


def generate_secret_key(length=32):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def load_existing_secrets():
    """Parse existing secret.txt into a dict, returning empty dict if not found."""
    if not os.path.exists(SECRET_FILE):
        return {}
    result = {}
    with open(SECRET_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = [part.strip() for part in line.split('=', 1)]
            if value != 'EDIT_THIS':
                result[key] = value
    return result


def load_existing_users():
    """Parse existing users.json, returning the first user's name and password."""
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        users = json.loads(f.read())
    if users and users[0].get('password') != 'CHANGE_THIS_PASSWORD':
        return {'name': users[0].get('name'), 'password': users[0].get('password')}
    return {}


def extract_round_number(database_name):
    """Extract round number from a database name like 'sqlite:///odinfo-round-49.sqlite'."""
    import re
    match = re.search(r'round-(\d+)', database_name)
    return match.group(1) if match else None


def ask(prompt, default=None, required=True):
    """Prompt the user for input with an optional default."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    while True:
        value = input(full_prompt).strip()
        if not value and default:
            return default
        if value:
            return value
        if not required:
            return None
        print("  This field is required. Please enter a value.")


def setup_secret_file():
    existing = load_existing_secrets()

    print("\n--- OD Info Configuration ---\n")

    username = ask("Your OpenDominion username", default=existing.get('username'))
    password = ask("Your OpenDominion password", default=existing.get('password'))

    print("\n  To find your player ID: go to the Search page in OpenDominion,")
    print("  hover over your dominion name, and note the number at the end")
    print("  of the '.../op-center/<number>' URL.")
    player_id = ask("Your player ID (number)", default=existing.get('current_player_id'))

    existing_round = extract_round_number(existing.get('database_name', ''))
    print("\n  The round number is used for the database file name.")
    print("  Each round gets its own database, so old data is preserved.")
    round_number = ask("Current round number", default=existing_round or "49")

    print("\n  Time shift: the difference in hours between your local time and OD server time.")
    print("  If OD shows 10:00 and your clock shows 12:00, enter -2.")
    print("  If OD shows 10:00 and your clock shows 8:00, enter 2.")
    time_shift = ask("Local time shift in hours", default=existing.get('LOCAL_TIME_SHIFT', '0'))

    discord_webhook = ask("Discord webhook URL (press Enter to skip)",
                          default=existing.get('discord_webhook'), required=False)

    secret_key = existing.get('secret_key') or generate_secret_key()

    lines = [
        "# ODInfo Configuration File\n",
        f"username = {username}\n",
        f"password = {password}\n",
    ]
    if discord_webhook:
        lines.append(f"discord_webhook = {discord_webhook}\n")
    lines.extend([
        f"current_player_id = {player_id}\n",
        f"database_name = sqlite:///odinfo-round-{round_number}.sqlite\n",
        f"secret_key = {secret_key}\n",
        f"LOCAL_TIME_SHIFT = {time_shift}\n",
    ])

    os.makedirs(INSTANCE_DIR, exist_ok=True)
    with open(SECRET_FILE, 'w') as f:
        f.writelines(lines)
    print(f"\n  Saved configuration to {SECRET_FILE}")


def setup_users_file():
    existing = load_existing_users()

    print("\n--- Web Login Setup ---\n")
    print("  OD Info runs a local web server. You need a login to access it.")
    print("  This is NOT your OpenDominion account - just a local login.\n")

    name = ask("Choose a username", default=existing.get('name', 'admin'))
    password = ask("Choose a password", default=existing.get('password'))

    users_json = f"""[
  {{
    "id": "1",
    "name": "{name}",
    "password": "{password}",
    "active": "true"
  }}
]
"""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        f.write(users_json)
    print(f"  Saved login to {USERS_FILE}")


def main():
    print("=" * 50)
    print("  Welcome to OD Info Setup")
    print("=" * 50)

    setup_secret_file()
    setup_users_file()

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("  Run odinfo.bat (Windows) or ./odinfo.sh (Mac/Linux) to start.")
    print("=" * 50 + "\n")


if __name__ == '__main__':
    main()