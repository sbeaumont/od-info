from rush.rankingscraper import load_stats
from config import OUT_DIR

EXCLUDE_STATS = ['Realm', 'Pack']
ROUND_NUMBER = 51


def to_include(stat_name: str) -> bool:
    for exclude_name in EXCLUDE_STATS:
        if exclude_name in stat_name:
            return False
    return True


def main():
    stats = load_stats(ROUND_NUMBER, to_include)

    title_holders = dict()
    for stat_name, rankings in stats.items():
        max_score = max([r.score for r in rankings.values()])
        stat_title_holders = [r for r in rankings.values() if r.score == max_score]
        title_holders[stat_name] = stat_title_holders

    with open(f'{OUT_DIR}/Title Holders Round {ROUND_NUMBER}.txt', 'w') as f:
        for stat, holders in title_holders.items():
            for player in holders:
                f.write(f"{stat},{player.player},{player.score}\n")


if __name__ == '__main__':
    main()
