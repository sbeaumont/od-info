"""
Save one real response of each OpenDominion API endpoint to docs/od_api/responses.

Run from the project root: uv run python -m docs.od_api.capture_api
"""

import json
import os

from odinfo.config import get_config
from odinfo.services.od_api import ODApi

RESPONSES_DIR = os.path.join(os.path.dirname(__file__), 'responses')


def save(name: str, data: dict | list):
    path = os.path.join(RESPONSES_DIR, f'{name}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved {path}")


def capture(api: ODApi):
    me = api.me()
    save('me', me)
    round_id = me['round']['id']
    save('rounds', api.rounds())
    save('dominions', api.dominions(round_id))
    save('realms', api.realms(round_id))
    save('events', api.events(round_id))
    save('advisors', api.advisors())
    op_center = api.op_center()
    save('op_center', op_center)
    target = next(dom['id'] for dom in op_center['dominions'].values() if dom['ops']['barracks_spy'])
    save('op_overview', api.op_overview(target))
    save('op_archive_barracks_spy', api.op_archive(target, 'barracks_spy'))


if __name__ == '__main__':
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    od_api = ODApi(get_config().api_key, on_wait=print)
    capture(od_api)
    od_api.close()