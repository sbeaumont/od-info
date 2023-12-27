from config import USERS_FILE
import json


class User(object):
    def __init__(self, user_info: dict):
        self.user_info = user_info
        self._authenticated = False

    @property
    def name(self):
        return self.user_info['name']

    @property
    def is_authenticated(self):
        return self._authenticated

    @property
    def is_active(self) -> bool:
        return self.user_info['active'] == "true"

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.user_info['id'])

    @property
    def password(self):
        return self.user_info['password']

    def __str__(self):
        return f"User({self.user_info})"


USERS = dict()


def get_user_by_id(_id: str | int) -> User | None:
    if _id in USERS:
        return USERS[_id]

    with open(USERS_FILE) as f:
        users = json.loads(f.read())
    for user in users:
        if str(_id) == str(user["id"]):
            USERS[user['id']] = User(user)
            return USERS[user['id']]
    return None


def get_user_by_name(name: str) -> User | None:
    for user in USERS.values():
        if str(name) == str(user.name):
            return user

    with open(USERS_FILE) as f:
        users = json.loads(f.read())
    for user in users:
        if str(name) == str(user["name"]):
            USERS[user['id']] = User(user)
            return USERS[user['id']]
    return None


if __name__ == "__main__":
    print(get_user_by_id(1))