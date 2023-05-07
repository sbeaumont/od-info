from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

EXCLUDE_STATS = ['Realm', 'Pack']
BASE_URL = 'https://www.opendominion.net/valhalla/round'
ROUND_NUMBER = 49

@dataclass
class Ranking:
    rank: int
    player: str
    score: int


def get_stat_page_urls(round_number: int):
    round_url = '/'.join([BASE_URL, str(round_number)])
    page = get_page(round_url)
    stat_page_urls = {link.text: link['href'] for link in page.find_all('a') if link['href'].startswith(round_url)}
    return stat_page_urls


def get_page(page_url: str) -> BeautifulSoup:
    page = requests.get(page_url)
    return BeautifulSoup(page.content, "html.parser")


def parse_entries_from_page(soup: BeautifulSoup) -> dict:
    results = dict()
    for line in soup.tbody.find_all('tr'):
        entry = [child.text.strip() for child in line.find_all('td')]
        ranking = Ranking(int(entry[0]), entry[2], int(entry[-1].replace(',', '')))
        results[ranking.player] = ranking
    return results


def load_stats(round_number: int):
    def to_include(stat_name: str) -> bool:
        for exclude_name in EXCLUDE_STATS:
            if exclude_name in stat_name:
                return False
        return True

    result = dict()
    stat_page_urls = get_stat_page_urls(round_number)
    blop_pages = {k: v for k, v in stat_page_urls.items() if to_include(k)}
    for name, url in blop_pages.items():
        page = get_page(url)
        page_stats = parse_entries_from_page(page)
        result[name] = page_stats
        print('Loaded', name)
    return result


if __name__ == '__main__':
    stats = load_stats(ROUND_NUMBER)
    title_holders = dict()
    for stat_name, rankings in stats.items():
        max_score = max([r.score for r in rankings.values()])
        stat_title_holders = [r for r in rankings.values() if r.score == max_score]
        title_holders[stat_name] = stat_title_holders

    with open(f'Title Holders Round {ROUND_NUMBER}.txt', 'w') as f:
        for stat, holders in title_holders.items():
            for player in holders:
                f.write(f"{stat},{player.player},{player.score}\n")
