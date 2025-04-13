from sqlalchemy import Integer, String, DateTime, ForeignKey, Float, func, JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, backref
from datetime import datetime
from typing import List, Optional

from odinfo.domain.domainhelper import Buildings, Land, Technology, Magic
from odinfo.timeutils import hours_since
from odinfo.domain.refdata import Race


class Base(DeclarativeBase):
    pass


class TimestampedOpsMixin(object):
    dominion_id = mapped_column('dominion', ForeignKey('Dominions.code'))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    __mapper_args__ = {'primary_key': [dominion_id, timestamp]}


class Dominion(Base):
    __tablename__ = 'Dominions'

    code: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    realm: Mapped[int] = mapped_column(Integer)
    race: Mapped[str] = mapped_column('race', String(200))
    player: Mapped[str] = mapped_column(String(200), default='?')
    role: Mapped[str] = mapped_column(String(12), default='unknown')
    last_op: Mapped[Optional[datetime]] = mapped_column(DateTime)
    history: Mapped[List['DominionHistory']] = relationship('DominionHistory',
                                                            back_populates='dom',
                                                            order_by='DominionHistory.timestamp.desc()')
    clear_sight: Mapped[List['ClearSight']] = relationship('ClearSight',
                                                  back_populates='dom',
                                                  order_by='ClearSight.timestamp.desc()')
    barracks_spy: Mapped[List['BarracksSpy']] = relationship('BarracksSpy',
                                                         back_populates='dom',
                                                         order_by='BarracksSpy.timestamp.desc()')
    castle_spy: Mapped[List['CastleSpy']] = relationship('CastleSpy',
                                                     back_populates='dom',
                                                     order_by='CastleSpy.timestamp.desc()')
    land_spy: Mapped[List['LandSpy']] = relationship('LandSpy',
                                                     back_populates='dom',
                                                     order_by='LandSpy.timestamp.desc()')
    revelation: Mapped[List['Revelation']] = relationship('Revelation',
                                                     back_populates='dom',
                                                     order_by='Revelation.timestamp.desc()')
    survey_dominion: Mapped[List['SurveyDominion']] = relationship('SurveyDominion',
                                                     back_populates='dom',
                                                     order_by='SurveyDominion.timestamp.desc()')
    vision: Mapped[List['Vision']] = relationship('Vision',
                                                     back_populates='dom',
                                                     order_by='Vision.timestamp.desc()')

    @property
    def current_land(self) -> int:
        return self.history[0].land

    @property
    def current_networth(self) -> int:
        return self.history[0].networth

    @property
    def military(self) -> dict | None:
        result = None
        if self.last_cs and self.last_barracks:
            cs_age = hours_since(self.last_cs.timestamp)
            bs_age = hours_since(self.last_barracks.timestamp)
            if (cs_age < 1) or (cs_age <= bs_age):
                result = self.last_cs.military
                # Add remaining training troops from last BS
                for i in range(1, 5):
                    result[f'unit{i}'] += self.last_barracks.aged_amount_training_for_unit(i)
                result['paid_until'] = self.last_barracks.paid_until
            else:
                result = self.last_barracks.military
        elif self.last_cs:
            result = self.last_cs.military
        elif self.last_barracks:
            result = self.last_barracks.military
        return result

    @property
    def navy(self) -> dict | None:
        if self.last_cs and self.last_survey:
            return {
                'docks': self.last_survey.dock,
                'boats': self.last_cs.resource_boats,
                'timestamp': min(self.last_cs.timestamp, self.last_survey.timestamp)
            }
        else:
            return None

    @property
    def race_obj(self) -> Race:
        if not hasattr(self, '_race_obj'):
            self._race_obj = Race(self, self.race)
        return self._race_obj

    @property
    def tech(self) -> Technology:
        return Technology(self)

    @property
    def magic(self) -> Magic:
        return Magic(self, self.revelation)

    @property
    def buildings(self) -> Buildings:
        return Buildings(self, self.last_survey) if self.last_survey else None

    @property
    def land(self) -> Land:
        return Land(self, self.last_land) if self.last_land else None

    @property
    def last_barracks(self):
        return self.barracks_spy[0] if self.barracks_spy else None

    @property
    def last_castle(self):
        return self.castle_spy[0] if self.castle_spy else None

    @property
    def last_cs(self):
        return self.clear_sight[0] if self.clear_sight else None

    @property
    def last_land(self):
        return self.land_spy[0] if self.land_spy else None

    @property
    def last_revelation(self):
        return self.revelation[0] if self.revelation else None

    @property
    def last_survey(self):
        return self.survey_dominion[0] if self.survey_dominion else None

    @property
    def last_vision(self):
        return self.vision[0] if self.vision else None

    def add_last_op(self, potential_last_op: datetime):
        if not self.last_op or (potential_last_op > self.last_op):
            self.last_op = potential_last_op

    @property
    def last_op_since(self) -> int:
        return hours_since(self.last_op)

    def __repr__(self):
        return f'Dominion({self.code}, {self.name}, {self.realm}, {self.race}, {self.player}, {self.role}, {self.last_op})'


class DominionHistory(TimestampedOpsMixin, Base):
    __tablename__ = 'DominionHistory'
    dom: Mapped['Dominion'] = relationship(back_populates='history')
    land: Mapped[int] = mapped_column(Integer)
    networth: Mapped[int] = mapped_column(Integer)

    def __repr__(self):
        return f'DominionHistory({self.dominion_id}, {self.timestamp}, {self.land}, {self.networth})'


class BarracksSpy(TimestampedOpsMixin, Base):
    BS_UNCERTAINTY: float = 0.85

    __tablename__ = 'BarracksSpy'
    dom: Mapped['Dominion'] = relationship(back_populates='barracks_spy')
    draftees: Mapped[int] = mapped_column(Integer, default=0)
    home_unit1: Mapped[int] = mapped_column(Integer, default=0)
    home_unit2: Mapped[int] = mapped_column(Integer, default=0)
    home_unit3: Mapped[int] = mapped_column(Integer, default=0)
    home_unit4: Mapped[int] = mapped_column(Integer, default=0)
    training: Mapped[dict] = mapped_column(JSON, default=JSON.NULL)
    returning: Mapped[dict] = mapped_column('return', JSON, default=JSON.NULL)

    def amount_training(self, unit_type_nr: int) -> int:
        if self.training:
            key = f'unit{unit_type_nr}'
            return sum(self.training[key].values()) if key in self.training else 0
        else:
            return 0

    def aged_amount_training_for_unit(self, unit_type_nr: int) -> int:
        key = f'unit{unit_type_nr}'
        age = hours_since(self.timestamp)
        if self.training and key in self.training:
            return sum([amount for tick, amount in self.training[key].items() if int(tick) - age > 0])
        else:
            return 0

    @property
    def aged_amount_training(self) -> int:
        return sum([self.aged_amount_training_for_unit(i) for i in range(1, 5)])

    def amount_returning(self, unit_type_nr: int) -> int:
        if self.returning:
            key = f'unit{unit_type_nr}'
            return sum(self.returning[key].values()) if key in self.returning else 0
        else:
            return 0

    @property
    def military(self) -> dict:
        def calc_unit(nr: int):
            home = getattr(self, f'home_unit{nr}') / BarracksSpy.BS_UNCERTAINTY
            away = self.amount_returning(nr) * BarracksSpy.BS_UNCERTAINTY
            training = self.amount_training(nr) if self.paid_until_for_unit(nr) > 0 else 0
            return home + away + training

        return {
            'unit1': calc_unit(1),
            'unit2': calc_unit(2),
            'unit3': calc_unit(3),
            'unit4': calc_unit(4),
            'draftees': self.draftees,
            'timestamp': self.timestamp,
            'paid_until': self.paid_until
        }

    def paid_until_for_unit(self, nr):
        age = hours_since(self.timestamp)
        max_ticks = 0
        key = f'unit{nr}'
        if key in self.training:
            max_ticks = max(max_ticks, max([int(t) for t in self.training[key]]))
        return max(0, max_ticks - age)

    @property
    def paid_until(self) -> int:
        return max([self.paid_until_for_unit(i) for i in range(1, 5)])

    def __repr__(self):
        return (f'BarracksSpy({self.dominion_id}, '
                f'{self.timestamp}, {self.draftees}, '
                f'{self.home_unit1}, {self.home_unit2}, '
                f'{self.home_unit3}, {self.home_unit4}, '
                f'{self.training}, {self.returning})')


class CastleSpy(TimestampedOpsMixin, Base):
    __tablename__ = 'CastleSpy'
    dom: Mapped['Dominion'] = relationship(back_populates='castle_spy')
    science_points: Mapped[int] = mapped_column(Integer, default=0)
    science_rating: Mapped[float] = mapped_column(Float, default=0)
    keep_points: Mapped[int] = mapped_column(Integer, default=0)
    keep_rating: Mapped[float] = mapped_column(Float, default=0)
    spires_points: Mapped[int] = mapped_column(Integer, default=0)
    spires_rating: Mapped[float] = mapped_column(Float, default=0)
    forges_points: Mapped[int] = mapped_column(Integer, default=0)
    forges_rating: Mapped[float] = mapped_column(Float, default=0)
    walls_points: Mapped[int] = mapped_column(Integer, default=0)
    walls_rating: Mapped[float] = mapped_column(Float, default=0)
    harbor_points: Mapped[int] = mapped_column(Integer, default=0)
    harbor_rating: Mapped[float] = mapped_column(Float, default=0)


class ClearSight(TimestampedOpsMixin, Base):
    __tablename__ = 'ClearSight'
    dom: Mapped['Dominion'] = relationship(back_populates='clear_sight')
    land: Mapped[int] = mapped_column(Integer)
    peasants: Mapped[int] = mapped_column(Integer)
    networth: Mapped[int] = mapped_column(Integer)
    prestige: Mapped[int] = mapped_column(Integer)
    resource_platinum: Mapped[int] = mapped_column(Integer)
    resource_food: Mapped[int] = mapped_column(Integer, default=0)
    resource_lumber: Mapped[int] = mapped_column(Integer, default=0)
    resource_mana: Mapped[int] = mapped_column(Integer, default=0)
    resource_ore: Mapped[int] = mapped_column(Integer, default=0)
    resource_gems: Mapped[int] = mapped_column(Integer, default=0)
    resource_boats: Mapped[int] = mapped_column(Integer, default=0)
    military_draftees: Mapped[int] = mapped_column(Integer, default=0)
    military_unit1: Mapped[int] = mapped_column(Integer, default=0)
    military_unit2: Mapped[int] = mapped_column(Integer, default=0)
    military_unit3: Mapped[int] = mapped_column(Integer, default=0)
    military_unit4: Mapped[int] = mapped_column(Integer, default=0)
    military_spies: Mapped[int] = mapped_column(Integer, default=0)
    military_assassins: Mapped[int] = mapped_column(Integer, default=0)
    military_wizards: Mapped[int] = mapped_column(Integer, default=0)
    military_archmages: Mapped[int] = mapped_column(Integer, default=0)
    clear_sight_accuracy: Mapped[float] = mapped_column(Float, default=0.85)
    wpa: Mapped[Optional[float]] = mapped_column(Float)

    @hybrid_property
    def military(self) -> dict:
        return {
            'unit1': self.military_unit1,
            'unit2': self.military_unit2,
            'unit3': self.military_unit3,
            'unit4': self.military_unit4,
            'draftees': self.military_draftees,
            'timestamp': self.timestamp
        }

    @hybrid_property
    def spywiz(self):
        return self.military_spies, self.military_assassins, self.military_wizards, self.military_archmages


class LandSpy(TimestampedOpsMixin, Base):
    __tablename__ = 'LandSpy'
    dom: Mapped['Dominion'] = relationship(back_populates='land_spy')
    total: Mapped[int] = mapped_column(Integer)
    barren: Mapped[int] = mapped_column(Integer)
    constructed: Mapped[int] = mapped_column(Integer)
    plain: Mapped[int] = mapped_column(Integer)
    plain_constructed: Mapped[int] = mapped_column(Integer)
    mountain: Mapped[int] = mapped_column(Integer)
    mountain_constructed: Mapped[int] = mapped_column(Integer)
    swamp: Mapped[int] = mapped_column(Integer)
    swamp_constructed: Mapped[int] = mapped_column(Integer)
    cavern: Mapped[int] = mapped_column(Integer)
    cavern_constructed: Mapped[int] = mapped_column(Integer)
    forest: Mapped[int] = mapped_column(Integer)
    forest_constructed: Mapped[int] = mapped_column(Integer)
    hill: Mapped[int] = mapped_column(Integer)
    hill_constructed: Mapped[int] = mapped_column(Integer)
    water: Mapped[int] = mapped_column(Integer)
    water_constructed: Mapped[int] = mapped_column(Integer)
    incoming: Mapped[dict] = mapped_column(JSON, default=JSON.NULL)


class Revelation(Base):
    __tablename__ = 'Revelation'
    dominion_id = mapped_column('dominion', ForeignKey('Dominions.code'))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())
    dom: Mapped['Dominion'] = relationship(back_populates='revelation')
    spell: Mapped[str] = mapped_column(String(80))
    duration: Mapped[int] = mapped_column(Integer)
    __mapper_args__ = {'primary_key': [dominion_id, timestamp, spell]}


class SurveyDominion(TimestampedOpsMixin, Base):
    __tablename__ = 'SurveyDominion'
    dom: Mapped['Dominion'] = relationship(back_populates='survey_dominion')
    home: Mapped[int] = mapped_column(Integer)
    alchemy: Mapped[int] = mapped_column(Integer, default=0)
    farm: Mapped[int] = mapped_column(Integer, default=0)
    smithy: Mapped[int] = mapped_column(Integer, default=0)
    masonry: Mapped[int] = mapped_column(Integer, default=0)
    ore_mine: Mapped[int] = mapped_column(Integer, default=0)
    gryphon_nest: Mapped[int] = mapped_column(Integer, default=0)
    tower: Mapped[int] = mapped_column(Integer, default=0)
    wizard_guild: Mapped[int] = mapped_column(Integer, default=0)
    temple: Mapped[int] = mapped_column(Integer, default=0)
    diamond_mine: Mapped[int] = mapped_column(Integer, default=0)
    school: Mapped[int] = mapped_column(Integer, default=0)
    lumberyard: Mapped[int] = mapped_column(Integer, default=0)
    factory: Mapped[int] = mapped_column(Integer, default=0)
    guard_tower: Mapped[int] = mapped_column(Integer, default=0)
    shrine: Mapped[int] = mapped_column(Integer, default=0)
    barracks: Mapped[int] = mapped_column(Integer, default=0)
    dock: Mapped[int] = mapped_column(Integer, default=0)
    barren_land: Mapped[int] = mapped_column(Integer, default=0)
    total_land: Mapped[int] = mapped_column(Integer, default=0)
    constructing: Mapped[Optional[dict]] = mapped_column(JSON, default=JSON.NULL)


class Vision(TimestampedOpsMixin, Base):
    __tablename__ = 'Vision'
    dom: Mapped['Dominion'] = relationship(back_populates='vision')
    techs: Mapped[Optional[dict]] = mapped_column(JSON, default=JSON.NULL)


class TownCrier(Base):
    __tablename__ = 'TownCrier'

    timestamp: Mapped[datetime] = mapped_column(DateTime)
    origin: Mapped[int] = mapped_column(Integer)
    origin_name: Mapped[str] = mapped_column(String(200))
    target: Mapped[int] = mapped_column(Integer)
    target_name: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(200), default='other')
    amount: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String(300))

    __mapper_args__ = {'primary_key': [timestamp, origin, event_type, target]}


class SchemaVersion(Base):
    __tablename__ = 'SchemaVersion'

    timestamp: Mapped[datetime] = mapped_column(DateTime)
    version: Mapped[str] = mapped_column(String(30))

    __mapper_args__ = {'primary_key': [timestamp]}


def schema_version(db) -> str:
    return db.session.query(SchemaVersion, func.max(SchemaVersion.timestamp)).scalar().version
