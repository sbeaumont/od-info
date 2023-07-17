from domain.scrapetools import get_soup_page, read_server_time
from config import SEARCH_PAGE
from opsdata.schema import update_dominion

QRY_UPDATE_DOM = 'REPLACE INTO Dominions(code, name, realm, race) VALUES(?, ?, ?, ?)'
QRY_SELECT_ALL_DOMS = '''
    SELECT 
        d.code, d.name, d.realm, d.role, h.land, h.networth, d.race, max(timestamp) 
    FROM 
        Dominions d
    LEFT JOIN 
        DominionHistory H on d.code = H.code
    GROUP BY d.code
    ORDER BY h.land
'''


def all_doms(db):
    return db.query(QRY_SELECT_ALL_DOMS)


def name_for_code(db, dom_code):
    return db.query('SELECT name FROM Dominions WHERE code = :dom_code', {'dom_code': dom_code}, one=True)['name']


def update_dom_index(session, db):
    for line in grab_search(session):
        update_dominion(line, db)


def grab_search(session) -> list:
    soup = get_soup_page(session, SEARCH_PAGE)
    server_time = read_server_time(soup)

    search_lines = list()
    for row in soup.find(id='dominions-table').tbody.find_all('tr'):
        cells = row.find_all('td')
        dom_info = dict()
        dom_info['name'] = cells[0].a.string
        dom_info['code'] = cells[0].a['href'].split('/')[-1]
        dom_info['realm'] = cells[1].a['href'].split('/')[-1]
        dom_info['race'] = cells[2].string.strip()
        dom_info['land'] = int(cells[3].string.strip().replace(',', ''))
        dom_info['networth'] = int(cells[4].string.strip().replace(',', ''))
        dom_info['in_range'] = cells[5].string.strip()
        dom_info['timestamp'] = str(server_time)
        search_lines.append(dom_info)
    return search_lines

