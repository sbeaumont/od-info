from pprint import pprint
from cron import initialize_database
from odinfo.calculators.networthcalculator import get_latest_and_oldest_nw

engine = initialize_database()
latest, oldest = get_latest_and_oldest_nw(engine)

pprint(latest)

pprint(oldest)
