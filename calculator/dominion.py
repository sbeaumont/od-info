import json
import os
from calculator.ops import grab_search
from calculator.scrapetools import login
from config import DOM_INDEX


def dom_index(session, file_name: str):
    if os.path.exists(file_name):
        print(f'Doms file "{file_name}" already exists: please remove if you want to regen.')
        return

    index_info = list()
    for line in grab_search(session):
        dom = {
            'name': line[1],
            'code': line[2],
            'realm': line[3],
            'race': line[4]
        }
        index_info.append(dom)

    with open(file_name, 'w') as f:
        json.dump(index_info, f, indent=2)


with open(DOM_INDEX) as f:
    DOMS = json.load(f)


def name_for_code(dom_code):
    doms_with_code = [d for d in DOMS if d['code'] == dom_code]
    if len(doms_with_code) == 1:
        return doms_with_code[0]['name']
    elif len(doms_with_code) == 0:
        return None
    else:
        raise Exception(f"Two doms with same name! {doms_with_code}")


if __name__ == '__main__':
    session = login()
    dom_index(session, DOM_INDEX)
