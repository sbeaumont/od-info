from config import USERS_FILE
import json


class User(object):
    @classmethod
    def from_json(cls, json_data):
        u = cls(json_data)
        u._authenticated = json_data['authenticated']
        return u

    def __init__(self, user_info: dict):
        self._id = user_info["id"]
        self.name = user_info["name"]
        self.password = user_info["password"]
        self._active = user_info["active"]
        self._authenticated = False

    @property
    def is_authenticated(self):
        return self._authenticated

    @property
    def is_active(self) -> bool:
        return self._active == "true"

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self._id)

    def to_json(self):
        return {
            "id": self._id,
            "name": self.name,
            "password": self.password,
            "active": self.is_active,
            "authenticated": self._authenticated
        }


def load_user_by_id(_id: str | int) -> User | None:
    with open(USERS_FILE) as f:
        users = json.loads(f.read())
    for u in users:
        if str(_id) == str(u["id"]):
            return User(u)
    return None


def load_user_by_name(name: str) -> User | None:
    with open(USERS_FILE) as f:
        users = json.loads(f.read())
    for u in users:
        if str(name) == str(u["name"]):
            return User(u)
    return None


if __name__ == "__main__":
    print(get_user_by_id(1))