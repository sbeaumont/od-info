"""
- Update database based on freshly scraped data
- Pull relevant information from OD scraped page
- Check OP Center for newer scans

- Mostly uses the search page and the copy-ops JSON structure that is under the "Copy Ops" button on the site.
"""

import json
import logging
from datetime import datetime

import config
from domain.timeutils import cleanup_timestamp

from opsdata.scrapetools import get_soup_page, read_server_time
from config import OP_CENTER_URL, MY_OP_CENTER_URL, SEARCH_PAGE

logger = logging.getLogger('db-info.ops')


class Ops(object):
    """Convenience object to parse the copy_ops json structure."""
    def __init__(self, contents, dom_id):
        self.contents = contents
        self.dom_id = dom_id

    def q_exists(self, q_str, start_node=None) -> bool:
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            if path in current_node:
                current_node = current_node[path]
                if current_node is None:
                    return False
            else:
                return False
        return True

    def q(self, q_str, start_node=None):
        paths = q_str.split('.')
        current_node = start_node if start_node else self.contents
        for path in paths:
            try:
                current_node = current_node[path]
            except KeyError:
                logger.error("Tried to find %s in %s", path, current_node)
        return current_node

    @property
    def name(self) -> str:
        return self.q('status.name')

    @property
    def race(self) -> str:
        return self.q('status.race_name')

    @property
    def realm(self) -> int:
        return int(self.q('status.realm'))

    @property
    def land(self) -> int:
        return int(self.q('status.land'))

    @property
    def networth(self) -> int:
        return int(self.q('status.networth'))

    @property
    def timestamp(self) -> datetime:
        ts = self.q_exists('status.created_at')
        if ts:
            return cleanup_timestamp(self.q('status.created_at'))
        else:
            return datetime.now()

    @property
    def has_clearsight(self) -> bool:
        return self.q_exists('status.name')

    @property
    def has_vision(self) -> bool:
        return self.q_exists('vision.techs')

    @property
    def has_barracks(self) -> bool:
        return self.q_exists('barracks.units')

    @property
    def has_castle(self) -> bool:
        return self.q_exists('castle.total')

    @property
    def has_land(self) -> bool:
        return self.q_exists('land.totalLand')

    @property
    def has_survey(self) -> bool:
        return self.q_exists('survey.constructed')

    @property
    def has_revelation(self) -> bool:
        return self.q_exists('revelation.spells')


def grab_ops(session, dom_code: int) -> Ops | None:
    """Grabs the copy_ops JSON file for a specified dominion."""
    soup = get_soup_page(session, f'{OP_CENTER_URL}/{dom_code}')
    if soup:
        ops_json = soup.find('textarea', id='ops_json').string
        return Ops(json.loads(ops_json), dom_code)
    else:
        return None


def grab_my_ops(session) -> Ops:
    """Grabs the copy_ops JSON file for the player's dominion."""
    soup = get_soup_page(session, f'{MY_OP_CENTER_URL}')
    ops_json = soup.find('textarea', id='ops_json').string
    return Ops(json.loads(ops_json), config.current_player_id)


def grab_search(session) -> dict:
    """Grabs the search page from the OpenDominion site.
    :returns dict of dictionaries with the search page fields"""
    soup = get_soup_page(session, SEARCH_PAGE)
    server_time = read_server_time(soup)

    search_lines = dict()
    for row in soup.find(id='dominions-table').tbody.find_all('tr'):
        cells = row.find_all('td')
        dom_info = dict()
        dom_info['name'] = cells[0].a.string
        dom_info['code'] = int(cells[0].a['href'].split('/')[-1])
        dom_info['dominion'] = dom_info['code']
        dom_info['realm'] = int(cells[1].a['href'].split('/')[-1])
        dom_info['race'] = cells[2].string.strip()
        dom_info['land'] = int(cells[3].string.strip().replace(',', ''))
        dom_info['networth'] = int(cells[4].string.strip().replace(',', ''))
        dom_info['in_range'] = cells[5].string.strip()
        dom_info['timestamp'] = str(server_time)
        search_lines[dom_info['code']] = dom_info
    return search_lines


def get_last_scans(session) -> dict:
    """Grabs the OP Center page and returns the doms and timestamps.
    Used to check if any latest scans need to be updated into the tool."""
    soup = get_soup_page(session, OP_CENTER_URL)
    result = dict()
    for row in soup.tbody.find_all('tr'):
        cells = row.find_all('td')
        domcode = int(cells[0].a['href'].split('/')[-1])
        timestamp = cells[4].span.string.strip()
        result[domcode] = cleanup_timestamp(timestamp)
    return result
