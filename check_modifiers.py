"""
Our OP and DP bonus for each realmie, with only active spells and finished buildings, next to the game's modifiers.

Run: uv run python check_modifiers.py
"""

import yaml

from cron import initialize_database
from odinfo.calculators.military import MilitaryCalculator
from odinfo.config import get_config, REF_DATA_DIR
from odinfo.domain.refdata import (Spells, MAX_GRYPHON_NEST_BONUS, GN_OFFENSE_BONUS, MAX_GUARD_TOWER_BONUS,
                                   GT_DEFENSE_FACTOR)
from odinfo.services.od_api import ODApi


def load_spells() -> dict:
    with open(f'{REF_DATA_DIR}/spells.yml') as f:
        return yaml.safe_load(f)


def active_spell_bonus(spells: dict, active: list[str], race: str, perk: str) -> float:
    """The bonus of one perk from the spells that are active now, as a decimal."""
    race_key = Spells.race_key(race)
    total = 0
    for spell_key in active:
        spell = spells[spell_key]
        if race_key in spell.get('races', [race_key]):
            total += spell['perks'].get(perk, 0)
    return total / 100


def main():
    config = get_config()
    repo = initialize_database(config)
    od_api = ODApi(config.api_key, on_wait=print)
    advisors = od_api.advisors()['dominions']
    od_api.close()
    spells = load_spells()

    print(f"{'Dominion':30} {'Race':12} {'OP ours':>8} {'OP game':>8} {'diff':>7} "
          f"{'DP ours':>8} {'DP game':>8} {'diff':>7}  Active spells")
    for code, advisor in advisors.items():
        dom = repo.get_dominion(int(code))
        mc = MilitaryCalculator(dom)
        active = [s['spell'] for s in advisor['ops']['revelation']['spells']]
        gn_now = min(MAX_GRYPHON_NEST_BONUS, dom.buildings.ratio_of('gryphon_nest', include_paid=False) * GN_OFFENSE_BONUS)
        gt_now = min(MAX_GUARD_TOWER_BONUS, dom.buildings.ratio_of('guard_tower', include_paid=False) * GT_DEFENSE_FACTOR)
        offense = (mc.offense_bonus - mc.spell_offense_bonus - mc.gryphon_nest_bonus
                   + active_spell_bonus(spells, active, dom.race, 'offense') + gn_now)
        defense = (mc.defense_bonus - mc.spell_defense_bonus - mc.guard_tower_bonus
                   + active_spell_bonus(spells, active, dom.race, 'defense') + gt_now)
        game_offense = advisor['military']['offensive_modifier']
        game_defense = advisor['military']['defensive_modifier']
        print(f"{dom.name[:30]:30} {dom.race[:12]:12} "
              f"{offense * 100:8.2f} {game_offense:8.2f} {offense * 100 - game_offense:7.2f} "
              f"{defense * 100:8.2f} {game_defense:8.2f} {defense * 100 - game_defense:7.2f}  {', '.join(active)}")


if __name__ == '__main__':
    main()