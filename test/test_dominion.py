import unittest

from test.fixtures import create_db_session, init_db
from domain.models import Dominion


class DominionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.session = create_db_session()
        init_db(self.session)

    def test_something(self):
        dom = self.session.get(Dominion, 1)
        self.assertEqual(dom.code, 1)  # add assertion here
        self.assertEqual(dom.last_cs.military_unit1, 10)


if __name__ == '__main__':
    unittest.main()


    # with Session(engine) as session:
    #     stmt = select(Dominion).where(Dominion.code == 11725)
    #     dom = session.scalars(stmt).one()
    #     print("Last barracks", dom.last_barracks)
    #     print("Last castle", str(dom.last_castle.keep_points))
    #     print(f"Last CS: {getattr(dom.last_cs, 'land')} {dom.last_cs.military}")
    #     print(f"Last LS {dom.last_land.total}")
    #     print(f"Last Rev {dom.last_revelation.spell}")
    #     print(f"Last survey {dom.last_survey.constructing}")
    #     print(f"Last vision {dom.vision}")
    #     print(schema_version())
    #     print(session.query(TownCrier, func.max(TownCrier.timestamp)).scalar().origin_name)
    #     print(dom.last_land.incoming)
    #     print(dom.name)
    #
    # with Session(engine) as session:
    #     stmt = select(Dominion)
    #     for row in session.scalars(stmt):
    #         print(row)
    #
    #     stmt = select(DominionHistory, func.max(DominionHistory.timestamp)
    #                   ).group_by(DominionHistory.dominion_id)
    #     for row in session.scalars(stmt):
    #         print(row)

    # with Session(engine) as session:
    #     latest_time = datetime.strptime('2024-02-29 22:40:40', '%Y-%m-%d %H:%M:%S')
    #     since_timestamp = latest_time + timedelta(hours=-12)
    #     print(since_timestamp)
    #     since_timestamp = datetime.now() - timedelta(hours=-12)
    #     latest_nws = session.execute(select(DominionHistory, func.max(DominionHistory.timestamp))
    #                                  .filter(DominionHistory.timestamp >= since_timestamp)
    #                                  .group_by(DominionHistory.dominion_id)).scalars()
    #     for nws in latest_nws:
    #         print(nws)
    #     print(latest_nws.first())
    #
    #     oldest_nws = session.execute(select(DominionHistory, func.min(DominionHistory.timestamp))
    #                                  .filter(DominionHistory.timestamp >= since_timestamp)
    #                                  .group_by(DominionHistory.dominion_id)).scalars()
    #
    #     for nws in oldest_nws:
    #         print(nws)
    #     print(oldest_nws.first())
    #
    #     doms = session.execute(select(Dominion)).scalars()
    #     for dom in doms:
    #         print(dom)
    #
    #     deltas = dict()
    #     for latest, oldest in zip(latest_nws, oldest_nws):
    #         deltas[latest.dominion_id] = latest.networth - oldest.networth
    #         print(latest.dominion_id, latest.networth, oldest.networth)

    # with Session(engine) as session:
    #     stmt = select(Dominion).where(Dominion.code == 42)
    #     dom = session.scalar(stmt)
    #     timestamp = datetime.utcnow()
    #     if not dom:
    #         dom = Dominion(code=42, name='Test Dominion', realm=1, _race='Wood Elf', last_op=timestamp)
    #         session.add(dom)
    #
    #     dh = DominionHistory(dominion_id=dom.code, timestamp=timestamp, land=100, networth=1000)
    #     dom.history.append(dh)
    #
    #     bs = BarracksSpy(dominion_id=42, timestamp=timestamp)
    #     dom.barracks_spy.append(bs)
    #
    #     session.commit()