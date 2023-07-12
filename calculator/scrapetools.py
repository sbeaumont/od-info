from pprint import pprint

import requests
from bs4 import BeautifulSoup

from config import LOGIN_URL, STATUS_URL
from secret import username, password


class ODTickTime(object):
    def __init__(self, day, tick, hh, mm):
        self.day = day
        self.tick = tick
        self.hh = hh
        self.mm = mm

    def __str__(self):
        return f'{self.day}.{self.tick}{self.hh}{self.mm}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.day}, {self.tick}, {self.hh}, {self.mm})'

    def __eq__(self, other):
        if other.__class__.__name__ == self.__class__.__name__:
            return str(self) == str(other)
        return False

    def __gt__(self, other):
        if other.__class__.__name__ == self.__class__.__name__:
            return float(str(self)) > float(str(other))
        return False


def print_response(res: requests.Response):
    print(f"\n{res.url}\n")
    pprint(res.text)
    print("\n====================\n")


def get_soup_page(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url)
    return BeautifulSoup(response.content, "html.parser")


def read_server_time(soup: BeautifulSoup) -> str:
    timestamp_span = [s for s in soup.footer.find_all('span') if s.has_attr('title')][0]
    return timestamp_span['title']


def read_tick_time(soup: BeautifulSoup) -> ODTickTime:
    timestamp_span = [s for s in soup.footer.find_all('span') if s.has_attr('title')][0]
    hh, mm = timestamp_span['title'].split(':')[-2:]
    strongs = timestamp_span.find_all('strong')
    day = strongs[0].string
    tick = strongs[1].string
    return ODTickTime(int(day), int(tick), int(hh), int(mm))


def login() -> requests.Session | None:
    session = requests.session()
    session.auth = (username, password)

    soup = get_soup_page(session, LOGIN_URL)
    csrf_token = soup.select_one('meta[name="csrf-token"]')['content']

    payload = {
        '_token': csrf_token,
        'email': username,
        'password': password
    }
    response = session.post(LOGIN_URL, data=payload)

    if response.status_code == 200:
        return session
    else:
        print("Login Failed.")
        return None


def test_ok():
    session = login()
    soup = get_soup_page(session, STATUS_URL)
    print("Server time is:", read_server_time(soup))
    print("Tick time is:", read_tick_time(soup), repr(read_tick_time(soup)))


if __name__ == '__main__':
    test_ok()

