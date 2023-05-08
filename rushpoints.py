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
from odscraper import load_stats

ROUND_NUMBER = 49
LAST_FIVE_ROUNDS = (49, 48, 47, 45, 44)
LAST_TEN_ROUNDS = (49, 48, 47, 45, 44, 42, 41, 39, 38, 36)

OUT_DIR = 'out/'

MASTERY_STATS = \
    ('Most Masterful Spies', 'Most Masterful Wizards')
OPS_STATS = \
    ('Most Successful Spies', 'Most Successful Wizards')
THEFT_STATS = \
    ('Top Platinum Thieves', 'Top Food Thieves', 'Top Lumber Thieves',
     'Top Mana Thieves', 'Top Ore Thieves', 'Top Gem Thieves')
BLACKOP_STATS = \
    ('Masters of Plague', 'Masters of Swarm', 'Masters of Air',
     'Masters of Lightning', 'Masters of Water', 'Masters of Earth', 'Top Snare Setters')
ASSASSINATION_STATS = \
    ('Most Spies Executed', 'Top Saboteurs', 'Top Magical Assassins',
     'Top Military Assassins', 'Most Wizards Executed', 'Top Spy Disbanders')
FIREBALL_STAT = \
    ('Masters of Fire',)

TOTAL_SCORE_RATIOS = {
    'Mastery': (MASTERY_STATS, 25),
    'Ops': (OPS_STATS, 35),
    'Theft': (THEFT_STATS, 10),
    'Blackops': (BLACKOP_STATS, 10),
    'Assassination': (ASSASSINATION_STATS, 5),
    'Fireball': (FIREBALL_STAT, 10)
}


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


def round_scores(round_number: int):
    blop_scores = blop_scores_for_round(round_number)
    top_blop = sorted(blop_scores, key=lambda e: e[1], reverse=True)
    with open(f'{OUT_DIR}Top (Black) Oppers Round {round_number}.txt', 'w') as f:
        for p in top_blop:
            f.write(f"{p[0]}, {p[1]}\n")


def multiple_round_totals(round_numbers: list):
    player_totals = defaultdict(int)
    for nr in round_numbers:
        print(f'== ROUND {nr} ==')
        blop_scores = blop_scores_for_round(nr)
        for player, score in blop_scores:
            player_totals[player] += score
    top_blop = [(p, s) for p, s in player_totals.items()]
    top_blop_sorted = sorted(top_blop, key=lambda e: e[1], reverse=True)

    with open(f'{OUT_DIR}Top (Black) Oppers Last {len(round_numbers)} Rounds.txt', 'w') as f:
        for p in top_blop_sorted:
            f.write(f"{p[0]}, {round(p[1], 3)}\n")


class Player:
    def __init__(self, name: str, round_numbers: list):
        self.name = name
        self.round_scores = {nr: 0 for nr in round_numbers}

    def add_round_score(self, nr, score):
        self.round_scores[nr] = score

    @property
    def total_score(self):
        return round(sum(self.round_scores.values()), 3)

    def scores_text(self):
        nrs = sorted(self.round_scores.keys(), reverse=True)
        sorted_scores = [str(round(self.round_scores[nr], 3)) for nr in nrs]
        return ','.join(sorted_scores)


def multiple_round_scores(round_numbers: list):
    player_scores = dict()
    for nr in round_numbers:
        print(f'== ROUND {nr} ==')
        blop_scores = blop_scores_for_round(nr)
        for player, score in blop_scores:
            if player not in player_scores:
                player_scores[player] = Player(player, round_numbers)
            player_scores[player].add_round_score(nr, score)
    top_blop_sorted = sorted(player_scores.values(), key=lambda e: e.total_score, reverse=True)

    with open(f'{OUT_DIR}Top (Black) Oppers Last {len(round_numbers)} Rounds - full.txt', 'w') as f:
        for player in top_blop_sorted:
            f.write(f"{player.name},{player.total_score},{player.scores_text()}\n")


if __name__ == '__main__':
    # round_scores(ROUND_NUMBER)
    # multiple_round_totals(LAST_FIVE_ROUNDS)
    multiple_round_scores(LAST_FIVE_ROUNDS)

