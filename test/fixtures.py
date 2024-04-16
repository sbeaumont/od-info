from datetime import datetime, timedelta
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from domain.models import (Base, Dominion, DominionHistory, ClearSight,
                           BarracksSpy, CastleSpy, LandSpy, Revelation,
                           SurveyDominion, Vision, TownCrier)


def create_db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return Session(engine)


def init_db(session: Session) -> None:
    timestamp = datetime.now() + timedelta(hours=-10)
    with session:
        dom = Dominion(
            code=1,
            name="Dominion Name",
            realm=10,
            race="Dwarf"
        )
        session.add(dom)

        dom.barracks_spy.append(BarracksSpy(
            draftees=10,
            home_unit1=10,
            home_unit2=10,
            home_unit3=10,
            home_unit4=10,
            training=json.loads('{"spies": {"4": 10}, "unit3": {"4": 100, "6": 99}}'),
            returning='',
            timestamp=timestamp
        ))

        dom.castle_spy.append(CastleSpy(
            science_points=101,
            science_rating=0.1,
            keep_points=102,
            keep_rating=0.2,
            spires_points=103,
            spires_rating=0.3,
            forges_points=0,
            forges_rating=0,
            walls_points=0,
            walls_rating=0,
            harbor_points=106,
            harbor_rating=0.6,
            timestamp=timestamp
        ))

        dom.clear_sight.append(ClearSight(
            land=100,
            peasants=20,
            networth=10001,
            prestige=300,
            resource_platinum=1100,
            resource_food=1200,
            resource_lumber=1300,
            resource_mana=1400,
            resource_ore=1500,
            resource_gems=1600,
            resource_boats=1700,
            military_draftees=10,
            military_unit1=10,
            military_unit2=10,
            military_unit3=10,
            military_unit4=10,
            military_spies=201,
            military_assassins=202,
            military_wizards=203,
            military_archmages=204,
            timestamp=timestamp
        ))

        dom.history.append(DominionHistory(
            land=100,
            networth=10000,
            timestamp=timestamp
        ))

        dom.land_spy.append(LandSpy(
            total=1000,
            barren=10,
            constructed=990,
            plain=100,
            plain_constructed=90,
            mountain=100,
            mountain_constructed=100,
            swamp=100,
            swamp_constructed=100,
            cavern=100,
            cavern_constructed=100,
            forest=100,
            forest_constructed=100,
            hill=100,
            hill_constructed=100,
            water=100,
            water_constructed=100,
            incoming=json.loads('{"hill": {"1": 5, "4": 5}, "plain": {"7": 10}}'),
            timestamp=timestamp
        ))

        dom.revelation.append(Revelation(
            spell="ares_call",
            duration=10,
            timestamp=timestamp
        ))

        dom.revelation.append(Revelation(
            spell="midas_touch",
            duration=10,
            timestamp=timestamp
        ))

        dom.survey_dominion.append(SurveyDominion(
            home=100,
            alchemy=50,
            farm=50,
            smithy=100,
            masonry=100,
            ore_mine=100,
            gryphon_nest=0,
            tower=100,
            wizard_guild=100,
            temple=0,
            diamond_mine=100,
            school=100,
            lumberyard=100,
            factory=100,
            guard_tower=0,
            shrine=100,
            barracks=100,
            dock=100,
            barren_land=10,
            total_land=1000,
            constructing=json.loads('{"school": {"6": 20}}'),
            timestamp=timestamp
        ))

        dom.vision.append(Vision(
            techs=json.loads('''{
                "tech_21_1": "Reforestation",
                "tech_20_3": "Architect's Touch",
                "tech_12_15": "Bunk Beds",
                "tech_11_17": "Carpenter's Knowhow",
                "tech_12_19": "Surveyor's Insight",
                "tech_11_21": "Battle Tactics"}'''),
            timestamp=timestamp
        ))

        session.add(TownCrier(
            origin=12345,
            origin_name="Origin Dominion",
            target=12123,
            target_name="Target Dominion",
            event_type="invasion",
            amount=75,
            text="TC invasion text",
            timestamp=timestamp
        ))

        session.commit()
