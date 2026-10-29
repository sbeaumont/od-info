import json
from functools import cache

from odinfo.config import USERS_FILE
from odinfo.exceptions import ODInfoException


class User(object):
    def __init__(self, user_info: dict):
        self._id = user_info["id"]
        self.name = user_info["name"]
        self.password = user_info["password"]
        self._active = user_info["active"]
        self._admin = user_info.get("admin", "false")

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self) -> bool:
        return self._active == "true"

    @property
    def is_admin(self) -> bool:
        return self._admin == "true"

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self._id)


@cache
def load_users() -> list[dict]:
    """The login entries in the users file."""
    with open(USERS_FILE) as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ODInfoException(f"Error reading {USERS_FILE}") from e


def load_user_by_id(_id: str | int) -> User | None:
    for u in load_users():
        if str(_id) == str(u["id"]):
            return User(u)
    return None


def load_user_by_name(name: str) -> User | None:
    for u in load_users():
        if str(name) == str(u["name"]):
            return User(u)
    return None


if __name__ == "__main__":
    print(get_user_by_id(1))