"""
Core of the webscraping functionality.

- Knows how to create a valid OD session for the user
- Pulls in whole page for other code to parse
- Knows how to deal with OD time versus "real"/system time.
"""

import requests
import logging
from bs4 import BeautifulSoup

from odinfo.config import LOGIN_URL, STATUS_URL, SELECT_URL, username, password, current_player_id
from requests.exceptions import TooManyRedirects


logger = logging.getLogger('od-info.scraping')


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


def get_soup_page(session: requests.Session, url: str) -> BeautifulSoup | None:
    logger.debug(f"Getting page {url}")
    try:
        response = session.get(url)
        return BeautifulSoup(response.content, "html.parser")
    except TooManyRedirects:
        return None


def read_server_time(soup: BeautifulSoup) -> str | None:
    list_o_titles = [s for s in soup.footer.find_all('span', title=True)]
    if len(list_o_titles) > 0:
        timestamp_span = list_o_titles[0]
        return timestamp_span['title']
    else:
        print("Can't find server time!")
        print(soup.footer.find_all('span'))
        print('\n', soup.footer)
        return None


def read_tick_time(soup: BeautifulSoup) -> ODTickTime:
    timestamp_element = [s for s in soup.footer.find_all('span') if s.has_attr('title')]
    if len(timestamp_element) > 0:
        timestamp_span = timestamp_element[0]
        hh, mm = timestamp_span['title'].split(':')[-2:]
        strongs = timestamp_span.find_all('strong')
        day = strongs[0].string
        tick = strongs[1].string
        return ODTickTime(int(day), int(tick), int(hh), int(mm))
    else:
        return ODTickTime(0, 0, 0, 0)


def pull_csrf_token(soup):
    if soup is None:
        raise ValueError("Cannot extract CSRF token: soup is None")
    csrf_element = soup.select_one('meta[name="csrf-token"]')
    if csrf_element is None:
        raise ValueError("CSRF token not found in page HTML")
    return csrf_element['content']


def login(for_player_id=None) -> requests.Session | None:
    session = requests.session()
    session.auth = (username, password)

    soup = get_soup_page(session, LOGIN_URL)
    payload = {
        '_token': pull_csrf_token(soup),
        'email': username,
        'password': password
    }
    response = session.post(LOGIN_URL, data=payload)

    if response.status_code == 200:
        if for_player_id:
            s2 = BeautifulSoup(response.content, "html.parser")
            response = select_current_dominion(session, pull_csrf_token(s2), current_player_id)
            if response.status_code != 200:
                print("Could not switch to other player")
                return None
        return session
    else:
        print(f"Login Failed. {response.status_code}, {response.text}")
        return None


def select_current_dominion(session, csrf_token, player_id):
    payload = {
        '_token': csrf_token
    }
    return session.post(SELECT_URL.format(str(player_id)), data=payload)


def test_ok():
    session = login(current_player_id)
    soup = get_soup_page(session, STATUS_URL)
    print(soup.contents)
    print("Server time is:", read_server_time(soup))
    print("Tick time is:", read_tick_time(soup), repr(read_tick_time(soup)))


if __name__ == '__main__':
    test_ok()

