"""
Generates CSV export of the military units of each race.

Each row is one unit type (4 rows per race)
"""

import yaml
import os
from odinfo.config import REF_DATA_DIR, OUT_DIR
from dataclasses import dataclass, astuple


@dataclass
class Unit(object):
    race: str
    name: str
    home_land: str
    platinum: int
    lumber: int
    ore: int
    mana: int
    gems: int
    offense: int
    defense: int
    perks: str


units = list()
race_dir = os.path.join(REF_DATA_DIR, 'races')
for filename in os.listdir(race_dir):
    with open(os.path.join(race_dir, filename)) as f:
        race = yaml.safe_load(f)

    for u in race['units']:
        cost = u['cost']
        perks = ''
        if 'perks' in u:
            perks = ', '.join([f'{k}: {v}' for k, v in u['perks'].items()])
        for cost_type in cost:
            if cost_type not in ('platinum', 'lumber', 'ore', 'mana', 'gems'):
                raise Exception(f"Need cost type {cost_type}")
        unit = Unit(
            race['name'],
            u['name'],
            race['home_land_type'],
            cost['platinum'],
            cost['lumber'] if 'lumber' in cost else 0,
            cost['ore'] if 'ore' in cost else 0,
            cost['mana'] if 'mana' in cost else 0,
            cost['gems'] if 'gems' in cost else 0,
            u['power']['offense'],
            u['power']['defense'],
            perks
        )
        units.append(unit)

output_file = os.path.join(OUT_DIR, 'unit_overview.csv')
print(f"Writing unit overview to {output_file}")

with open(output_file, 'w') as f:
    field_names = ["Race", "Name", "Home Land", "Platinum", "Lumber", "Ore", "Mana", "Gems", "Base Offense", "Base Defense", "Perks"]
    title_row = f'''"{'", "'.join(field_names)}"'''
    print(title_row)
    f.write(f'{title_row}\n')
    for unit in units:
        fields = '", "'.join([str(fld) for fld in astuple(unit)])
        print(f'"{fields}"')
        f.write(f'"{fields}"\n')
