from pprint import pprint

import requests
from bs4 import BeautifulSoup

from config import LOGIN_URL, STATUS_URL
from secret import username, password


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


def read_tick_time(soup: BeautifulSoup) -> str:
    timestamp_span = [s for s in soup.footer.find_all('span') if s.has_attr('title')][0]
    timestamp_hhmm = ''.join(timestamp_span['title'].split(':')[-2:])
    strongs = timestamp_span.find_all('strong')
    day = strongs[0].string
    tick = strongs[1].string
    return f'{day}.{tick}{timestamp_hhmm}'


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
    print("Tick time is:", read_tick_time(soup))


if __name__ == '__main__':
    test_ok()

