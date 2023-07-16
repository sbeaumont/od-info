from domain.scrapetools import get_soup_page, read_tick_time
from config import SEARCH_PAGE

QRY_UPDATE_DOM = 'INSERT OR REPLACE INTO Dominions(code, name, realm, race, land, networth) VALUES(?, ?, ?, ?, ?, ?)'
QRY_SELECT_ALL_DOMS = 'SELECT code, name, realm, land, networth, role, race FROM Dominions ORDER BY land'


def all_doms(db):
    return db.query(QRY_SELECT_ALL_DOMS)


def update_dom_index(session, db):
    cur = db.cursor()
    for line in grab_search(session):
        qry_params = (line['code'],
                      line['name'],
                      line['realm'],
                      line['race'],
                      line['land'],
                      line['networth'])
        cur.execute(QRY_UPDATE_DOM, qry_params)
    db.commit()


def grab_search(session) -> list:
    soup = get_soup_page(session, SEARCH_PAGE)
    server_time = read_tick_time(soup)

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
