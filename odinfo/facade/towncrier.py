from bs4 import BeautifulSoup
import re
import logging

from odinfo.config import OUT_DIR, TOWN_CRIER_URL
from odinfo.exceptions import ODInfoException
from odinfo.opsdata.scrapetools import expect_not_none

logger = logging.getLogger('od-info.towncrier')


class TownCrierParseError(ODInfoException):
    """Exception raised when Town Crier event text cannot be parsed."""
    
    def __init__(self, event_text):
        message = f"Did not recognize Town Crier event format: {event_text[:200]}{'...' if len(event_text) > 200 else ''}"
        super().__init__(message, {'event_text': event_text})


def get_number_of_tc_pages(session) -> int:
    response = session.get(TOWN_CRIER_URL)
    soup = BeautifulSoup(response.content, "html.parser")
    tc_page_urls = soup.find_all('a', href=re.compile(r'.*\/town-crier\?page=(\d+)'))
    page_numbers = [int(url['href'].split('page=')[-1]) for url in tc_page_urls]
    return max(page_numbers) if page_numbers else 1


def get_tc_page(session, page_nr: int) -> list:
    events = list()
    response = session.get(f'{TOWN_CRIER_URL}?page={page_nr}')
    soup = BeautifulSoup(response.content, "html.parser")
    cs = expect_not_none(
        soup.find('table', class_='table-striped'),
        f"the event table on town crier page {page_nr} ({response.url})"
    )
    for row in cs.find_all('tr'):
        if not row.td.has_attr('colspan'):
            events.append(_parse_event_row(row))
    return events


def _parse_event_row(row):
    columns = row.find_all('td')
    timestamp = columns[0].span.string
    event = columns[1]
    event_text = ' '.join(event.stripped_strings)

    # OD wraps every named entity (dom, realm, wonder) as <a><span>NAME</span>...</a>.
    # Anything outside <a><span> is verb-phrase prose (or amounts, realm "(#N)" markers).
    named = [a for a in event.find_all('a') if a.find('span') is not None]
    names = [a.find('span').get_text(strip=True) for a in named]
    hrefs = [a.attrs['href'] for a in named]

    # Build a name-free skeleton so dom names can't poison substring/regex matching.
    skeleton = event_text
    for n in sorted(names, key=len, reverse=True):
        skeleton = skeleton.replace(n, '<DOM>')

    # Realm number "(#N)" follows each named entity in document order.
    realm_numbers = re.findall(r'<DOM>\s*\(#(\d+)\)', skeleton)

    def code(idx):
        return hrefs[idx].split('/')[-1]

    dom_name = names[0] if names else ''
    dom_code = code(0) if hrefs else ''
    target_name = names[1] if len(names) > 1 else ''
    target_code = code(1) if len(hrefs) > 1 else ''
    amount = ''

    try:
        if 'conquered' in skeleton:
            event_type = 'invasion'
            amount = re.search(r'conquered (\d+) land', skeleton).group(1)
        elif 'invaded fellow dominion' in skeleton or 'invaded' in skeleton:
            event_type = 'invasion'
            amount = re.search(r'and captured (\d+)', skeleton).group(1)
        elif 'fended off an attack' in skeleton:
            event_type = 'bounce'
        elif 'were beaten back by' in skeleton:
            event_type = 'bounce'
            dom_name, target_name = names[1], names[0]
            dom_code, target_code = code(1), code(0)
        elif 'destroyed and rebuilt' in skeleton:
            event_type = 'wonder_destruction'
            target_name, dom_name = names[0], names[1]
            target_code = ' '
            dom_code = code(1)
        elif 'has attacked' in skeleton:
            if 'a neutral wonder' in skeleton:
                event_type = 'wonder_attack'
                target_name = 'a neutral wonder'
                target_code = ' '
            elif len(named) >= 2 and hrefs[1].endswith('/wonders'):
                event_type = 'wonder_attack'
                target_name = names[1]
                target_code = realm_numbers[1] if len(realm_numbers) > 1 else ' '
            elif len(named) >= 2:
                event_type = 'raid_attack'
                target_name = names[1]
                target_code = ' '
            else:
                m = re.search(r'has attacked ([^.]+)\.', skeleton)
                if m is None:
                    raise AttributeError("No matching attack pattern found")
                event_type = 'raid_attack'
                target_name = m.group(1).strip()
                target_code = ' '
        elif 'CANCELED' in skeleton:
            event_type = 'war_cancel'
        elif 'declared WAR' in skeleton:
            event_type = 'war_declare'
        elif 'abandoned' in skeleton:
            event_type = 'abandon'
            target_code = realm_numbers[0] if realm_numbers else ''
        else:
            event_type = 'other'
    except (AttributeError, IndexError) as e:
        logger.error(f'Error while parsing event text: {event_text}')
        raise TownCrierParseError(event_text) from e

    return [timestamp, event_type, dom_code, dom_name, target_code, target_name, amount, event_text]


if __name__ == '__main__':
    from odinfo.config import get_config
    from odinfo.services.od_session import ODSession
    with ODSession(get_config()) as od_session:
        with open(f'{OUT_DIR}/all_tc.txt', 'w') as f:
            for page_nr in range(1, get_number_of_tc_pages(od_session.session) + 1):
                events = get_tc_page(od_session.session, page_nr)
                for event in events:
                    event_line = f'''"{'", "'.join(event)}"'''
                    f.write(event_line)
                    f.write('\n')
                    print(event_line)
