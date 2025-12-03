from sqlalchemy import text
from sqlalchemy.orm import Session


class AwardStats(object):
    def __init__(self, session: Session):
        self._session = session

    @property
    def bouncy_castle_award(self):
        query = text("""
            select
                tc.target as code,
                tc.target_name as name,
                d.race as race,
                d.realm as realm,
                count(1) as amount
            from TownCrier tc
            left join Dominions d on tc.target = d.code
            where tc.event_type = 'bounce'
            group by tc.target
            order by amount desc""")
        return self._session.execute(query)

    @property
    def bouncy_loser_award(self):
        query = text("""
            select
                tc.origin as code,
                tc.origin_name as name,
                d.race as race,
                d.realm as realm,
                count(1) as amount
            from TownCrier tc
            left join Dominions d on tc.origin = d.code
            where tc.event_type = 'bounce'
            group by tc.origin
            order by amount desc""")
        return self._session.execute(query)

    @property
    def war_declarations(self):
        query = text("""
            select
                tc.origin as realm,
                tc.origin_name as name,
                count(1) as declarations
            from TownCrier tc
            where tc.event_type like 'war_declare'
            group by tc.origin
            order by declarations desc""")
        return self._session.execute(query)

    @property
    def declared_on(self):
        query = text("""
            select
                tc.target as realm,
                tc.target_name as name,
                count(1) as declared_on
            from TownCrier tc
            where tc.event_type like 'war_declare'
            group by tc.target
            order by declared_on desc""")
        return self._session.execute(query)

    @property
    def hits_taken(self):
        query = text("""
            select
                tc.target as code,
                tc.target_name as name,
                d.race as race,
                d.realm as realm,
                sum(tc.amount) as total_land,
                count(1) as total_hits
            from TownCrier tc
            left join Dominions d on tc.target = d.code
            group by tc.target
            having total_land > 0
            order by total_land desc""")
        return self._session.execute(query)

    @property
    def hits_done(self):
        query = text("""
            select
                tc.origin as code,
                tc.origin_name as name,
                d.race as race,
                d.realm as realm,
                sum(tc.amount) as total_land,
                count(1) as total_hits
            from TownCrier tc
            left join Dominions d on tc.origin = d.code
            group by tc.origin
            having total_land > 0
            order by total_land desc""")
        return self._session.execute(query)

    @property
    def abandons(self):
        query = text("""
            select
                tc.origin as code,
                tc.origin_name as name,
                d.race as race,
                tc.target as realm
            from TownCrier tc
            left join Dominions d on tc.origin = d.code
            where tc.event_type like 'abandon'
            group by tc.target""")
        return self._session.execute(query)
