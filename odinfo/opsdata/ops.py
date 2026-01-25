"""
- Update database based on freshly scraped data
- Pull relevant information from OD scraped page
- Check OP Center for newer scans

- Mostly uses the search page and the copy-ops JSON structure that is under the "Copy Ops" button on the site.
"""

import json
import logging
from datetime import datetime

from odinfo.timeutils import cleanup_timestamp, current_od_time

from odinfo.opsdata.scrapetools import get_soup_page, read_server_time
import re

from odinfo.config import OP_CENTER_URL, MY_OP_CENTER_URL, SEARCH_PAGE, BARRACKS_ARCHIVE_URL, get_config

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
            return current_od_time()

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
    return Ops(json.loads(ops_json), get_config().current_player_id)


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


class BarracksArchive:
    """Scrapes and parses barracks spy archive pages from OpenDominion."""

    def __init__(self, session, dom_code: int):
        self.session = session
        self.dom_code = dom_code

    def scrape(self, max_pages: int = 100) -> list[dict]:
        """Scrape all barracks spy entries from the archive.

        Returns:
            List of dicts with parsed BS data ready for BarracksSpy creation.
        """
        results = []
        page = 1

        while page <= max_pages:
            url = BARRACKS_ARCHIVE_URL.format(self.dom_code)
            if page > 1:
                url += f'?page={page}'

            logger.debug(f"Scraping barracks archive page {page} for dom {self.dom_code}")
            soup = get_soup_page(self.session, url)
            if soup is None:
                break

            home_boxes, returning_boxes = self._find_boxes(soup)
            if not home_boxes:
                break

            for i, home_box in enumerate(home_boxes):
                returning_box = returning_boxes[i] if i < len(returning_boxes) else None
                entry = self._parse_entry(home_box, returning_box)
                if entry:
                    results.append(entry)

            if not self._has_next_page(soup):
                break
            page += 1

        logger.info(f"Scraped {len(results)} barracks spy entries for dom {self.dom_code}")
        return results

    def _find_boxes(self, soup):
        """Find all home and returning unit boxes on the page."""
        home_boxes = []
        returning_boxes = []

        for box in soup.find_all('div', class_='box-primary'):
            title = box.find('h3', class_='box-title')
            if title:
                title_text = title.get_text()
                if 'Units in training and home' in title_text:
                    home_boxes.append(box)
                elif 'Units returning from battle' in title_text:
                    returning_boxes.append(box)

        return home_boxes, returning_boxes

    def _has_next_page(self, soup):
        """Check if there's a next page link."""
        pagination = soup.find('ul', class_='pagination')
        return pagination and pagination.find('a', rel='next')

    def _parse_entry(self, home_box, returning_box) -> dict | None:
        """Parse a single barracks spy entry."""
        timestamp = self._extract_timestamp(home_box)
        if not timestamp:
            return None

        table = home_box.find('table')
        if not table or not table.find('tbody'):
            return None

        draftees, home_units, training = self._parse_home_table(table)
        returning = self._parse_returning_table(returning_box) if returning_box else {}

        return {
            'timestamp': timestamp,
            'draftees': draftees,
            'home_unit1': home_units[0],
            'home_unit2': home_units[1],
            'home_unit3': home_units[2],
            'home_unit4': home_units[3],
            'training': training if training else None,
            'returning': returning if returning else None,
        }

    def _extract_timestamp(self, box) -> str | None:
        """Extract timestamp from box footer: 'Revealed YYYY-MM-DD HH:MM:SS by Player'."""
        footer = box.find('div', class_='box-footer')
        if not footer:
            return None

        em = footer.find('em')
        if not em:
            return None

        text = em.get_text()
        if not text.startswith('Revealed '):
            return None

        return text[9:28]  # "YYYY-MM-DD HH:MM:SS"

    def _parse_home_table(self, table):
        """Parse the home units table."""
        rows = table.find('tbody').find_all('tr')

        draftees = 0
        home_units = [0, 0, 0, 0]
        training = {}
        unit_idx = 0

        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue

            unit_name = cells[0].get_text().strip().rstrip(':')

            if unit_name in ('Spies', 'Assassins', 'Wizards', 'Archmages'):
                continue

            if unit_name == 'Draftees':
                draftees = self._parse_value(cells[-1].get_text())
            elif unit_idx < 4:
                home_units[unit_idx] = self._parse_value(cells[-1].get_text())
                unit_training = self._parse_tick_columns(cells)
                if unit_training:
                    training[f'unit{unit_idx + 1}'] = unit_training
                unit_idx += 1

        return draftees, home_units, training

    def _parse_returning_table(self, box) -> dict:
        """Parse the returning units table."""
        table = box.find('table')
        if not table or not table.find('tbody'):
            return {}

        rows = table.find('tbody').find_all('tr')
        returning = {}
        unit_idx = 0

        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue

            unit_name = cells[0].get_text().strip().rstrip(':')
            if unit_name == 'Draftees':
                continue

            if unit_idx < 4:
                unit_returning = self._parse_tick_columns(cells)
                if unit_returning:
                    returning[f'unit{unit_idx + 1}'] = unit_returning
                unit_idx += 1

        return returning

    def _parse_tick_columns(self, cells) -> dict:
        """Parse tick columns 1-12 into a dict."""
        result = {}
        for tick in range(1, 13):
            if tick < len(cells) - 1:  # -1 for home/total column
                value = self._parse_value(cells[tick].get_text())
                if value > 0:
                    result[str(tick)] = value
        return result

    def _parse_value(self, text: str) -> int:
        """Parse a unit value: '~3,227', '0', '-', '???'."""
        text = text.strip()
        if text in ('-', '???', ''):
            return 0
        return int(text.lstrip('~').replace(',', ''))
