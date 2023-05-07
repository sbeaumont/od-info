"""
Score Breakdown

Mastery Score
    Masterful Spies
    Masterful Wizards
Ops Score
    Successful Spies
    Successful Wizards
Theft Score
    Thieving Scores
Blackop Score
    Blackop Scores
Fireball Score

"""
from collections import defaultdict
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://www.opendominion.net/valhalla/round'
ROUND_NUMBER = 49
LAST_FIVE_ROUNDS = (49, 48, 47, 45, 44)
OUT_DIR = 'out/'
MASTERY_STATS = ('Most Masterful Spies', 'Most Masterful Wizards')
OPS_STATS = ('Most Successful Spies', 'Most Successful Wizards')
THEFT_STATS = ('Top Platinum Thieves', 'Top Food Thieves', 'Top Lumber Thieves', 'Top Mana Thieves',
               'Top Ore Thieves', 'Top Gem Thieves')
BLACKOP_STATS = ('Masters of Plague', 'Masters of Swarm', 'Masters of Air', 'Masters of Lightning',
                 'Masters of Water', 'Masters of Earth', 'Top Snare Setters')
ASSASSINATION_STATS = ('Most Spies Executed', 'Top Saboteurs', 'Top Magical Assassins', 'Top Military Assassins',
                       'Most Wizards Executed', 'Top Spy Disbanders')
FIREBALL_STAT = ('Masters of Fire',)

TOTAL_SCORE_RATIOS = {
    'Mastery': (MASTERY_STATS, 25),
    'Ops': (OPS_STATS, 35),
    'Theft': (THEFT_STATS, 10),
    'Blackops': (BLACKOP_STATS, 10),
    'Assassination': (ASSASSINATION_STATS, 5),
    'Fireball': (FIREBALL_STAT, 10)
}

@dataclass
class Ranking:
    rank: int
    player: str
    score: int
    fs_score: float = 0


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


def is_blop_stat(stat_name: str) -> bool:
    blop_keywords = ['Wizard', 'Spies', 'Thieves', 'Masters', 'Saboteurs', 'Snare', 'Spy', 'Assassins']
    for kw in blop_keywords:
        if kw in stat_name:
            return True
    return False


def feature_scaled_scores(rankings: dict, low=0, high=1):
    max_score = max([r.score for r in rankings.values()])
    min_score = min([r.score for r in rankings.values()])
    for r in rankings.values():
        r.fs_score = low + ((r.score - min_score) * (high - low)) / (max_score - min_score)


def load_stats(round_number: int):
    result = dict()
    stat_page_urls = get_stat_page_urls(round_number)
    blop_pages = {k: v for k, v in stat_page_urls.items() if is_blop_stat(k)}
    for name, url in blop_pages.items():
        page = get_page(url)
        page_stats = parse_entries_from_page(page)
        feature_scaled_scores(page_stats)
        result[name] = page_stats
        print('Loaded', name)
    return result


def all_player_names(stats: dict) -> list:
    players = set()
    for stat in stats.values():
        players.update(stat.keys())
    return players


def calculate_player_score(stats: dict, name: str) -> float:
    player_score = 0
    for score_component in TOTAL_SCORE_RATIOS.values():
        total = 0
        for stat_name in score_component[0]:
            if name in stats[stat_name]:
                total += stats[stat_name][name].fs_score
        component_score = total / len(score_component[0]) * score_component[1]
        player_score += component_score
    return round(player_score, 3)


def blop_scores_for_round(round_number: int) -> list:
    stats = load_stats(round_number)
    players = all_player_names(stats)
    return [(player, calculate_player_score(stats, player)) for player in players]


if __name__ == '__main__':
    blop_scores = blop_scores_for_round(ROUND_NUMBER)
    top_blop = sorted(blop_scores, key=lambda e: e[1], reverse=True)

    with open(f'{OUT_DIR}Top (Black) Oppers Round {ROUND_NUMBER}.txt', 'w') as f:
        for p in top_blop:
            f.write(f"{p[0]}, {p[1]}\n")

    last_five_rounds = defaultdict(int)
    for nr in LAST_FIVE_ROUNDS:
        print(f'== ROUND {nr} ==')
        blop_scores = blop_scores_for_round(nr)
        for player, score in blop_scores:
            last_five_rounds[player] += score
    top_5_blop = [(p, s) for p, s in last_five_rounds.items()]
    top_5_blop_sorted = sorted(top_5_blop, key=lambda e: e[1], reverse=True)

    with open(f'{OUT_DIR}Top (Black) Oppers Last Five Rounds.txt', 'w') as f:
        for p in top_5_blop_sorted:
            f.write(f"{p[0]}, {round(p[1], 3)}\n")

