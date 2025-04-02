from odinfo.config import OP_CENTER_URL
from odinfo.config import current_player_id
from odinfo.opsdata import login, get_soup_page


def go():
    session = login(current_player_id)
    soup = get_soup_page(session, OP_CENTER_URL)
    print(soup.tbody.tr)
    for row in soup.tbody.find_all('tr'):
        cells = row.find_all('td')
        print(cells[0].a.string.strip(), cells[0].a['href'].split('/')[-1], cells[4].span.string.strip())


if __name__ == '__main__':
    go()
