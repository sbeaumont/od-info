"""
Core of the webscraping functionality.

- Pulls in whole page for other code to parse
- Knows how to deal with OD time versus "real"/system time.

Note: Session management is in odinfo.services.od_session.ODSession.
"""

import requests
import logging
from bs4 import BeautifulSoup
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
        if response.status_code >= 500:
            raise ConnectionError(f"OpenDominion server error (HTTP {response.status_code})")
        if response.status_code >= 400:
            raise ConnectionError(f"Cannot reach OpenDominion: HTTP {response.status_code}")
        return BeautifulSoup(response.content, "html.parser")
    except TooManyRedirects:
        logger.warning(f"Too many redirects for {url} - likely session expired or page not accessible")
        return None
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Cannot reach OpenDominion: {e}")


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



