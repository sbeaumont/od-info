import time

from config import current_player_id
from opsdata.scrapetools import login, get_soup_page

FORUM_URL = 'https://www.opendominion.net/dominion/forum/330?page={}'


def go():
    comments = list()
    session = login(current_player_id)
    for page_nr in range(1, 99):
        url = FORUM_URL.format(page_nr)
        print(f"Loading page {url}")
        soup = get_soup_page(session, url)
        comments = soup.find_all('div', {'class': 'comment-text'})
        print("COMMENTS", comments)
        for comment in comments:
            print(comment)
            print(comment.p.text)
            comments.append(comment.p.text)
    with open('threewordstory-R38.txt', 'w') as f:
        f.write(' '.join(comments))


if __name__ == '__main__':
    start = time.time()
    go()
    end = time.time()
    print(end-start)