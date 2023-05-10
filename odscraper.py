from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from typing import Callable

BASE_URL = 'https://www.opendominion.net/valhalla/round'


@dataclass
class Ranking:
    rank: int
    player: str
    score: int
    fs_score: float = 0


def get_stat_page_urls(round_number: int):
    """Retrieve all stat page URLs from the stat overview page of the round."""
    round_url = '/'.join([BASE_URL, str(round_number)])
    page = get_page(round_url)
    stat_page_urls = {link.text: link['href'] for link in page.find_all('a') if link['href'].startswith(round_url)}
    return stat_page_urls


def get_page(page_url: str) -> BeautifulSoup:
    """Utility function to load a URL into a BeautifulSoup instance."""
    page = requests.get(page_url)
    return BeautifulSoup(page.content, "html.parser")


def parse_entries_from_page(soup: BeautifulSoup) -> dict:
    """Pull rankings out of a stat page."""
    results = dict()
    for line in soup.tbody.find_all('tr'):
        entry = [child.text.strip() for child in line.find_all('td')]
        ranking = Ranking(int(entry[0]), entry[2], int(entry[-1].replace(',', '')))
        results[ranking.player] = ranking
    return results


def feature_scaled_scores(rankings: dict, low=0, high=1):
    max_score = max([r.score for r in rankings.values()])
    min_score = min([r.score for r in rankings.values()])
    for r in rankings.values():
        r.fs_score = low + ((r.score - min_score) * (high - low)) / (max_score - min_score)


def load_stats(round_number: int, stat_filter: Callable[[str], int]):
    result = dict()
    stat_page_urls = get_stat_page_urls(round_number)
    blop_pages = {k: v for k, v in stat_page_urls.items() if stat_filter(k)}
    for name, url in blop_pages.items():
        page = get_page(url)
        page_stats = parse_entries_from_page(page)
        feature_scaled_scores(page_stats)
        result[name] = page_stats
        print('Loaded', name)
    return result
