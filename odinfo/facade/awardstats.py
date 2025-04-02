from sqlalchemy import text


class AwardStats(object):
    def __init__(self, db):
        self.db = db

    @property
    def bouncy_castle_award(self):
        query = text("""
            select 
                target as code, 
                target_name as name, 
                count(1) as amount
            from TownCrier
            where event_type = 'bounce'
            group by target
            order by amount desc""")
        return self.db.session.execute(query)

    @property
    def bouncy_loser_award(self):
        query = text("""select
                            origin as code,
                            origin_name as name, 
                            count(1) as amount
                        from
                            TownCrier
                        where
                            event_type = 'bounce'
                        group by
                            origin
                        order by
                            amount desc""")
        return self.db.session.execute(query)

    @property
    def war_declarations(self):
        query = text("""select
                            origin,
                            origin_name,
                            count(1) as declarations
                        from TownCrier
                        where
                            event_type like 'war_declare'
                        group by
                            origin
                        order by
                            declarations desc;""")
        return self.db.session.execute(query)

    @property
    def declared_on(self):
        query = text("""select
                            target,
                            target_name,
                            count(1) as declared_on
                        from TownCrier
                        where
                            event_type like 'war_declare'
                        group by
                            target
                        order by
                            declared_on desc;""")
        return self.db.session.execute(query)

    @property
    def hits_taken(self):
        query = text("""select
                            target as code,
                            target_name as name,
                            sum(amount) as total_land,
                            count(1) as total_hits
                        from
                            TownCrier
                        group by
                            target
                        having
                            total_land > 0
                        order by
                            total_land desc;""")
        return self.db.session.execute(query)

    @property
    def hits_done(self):
        query = text("""select
                            origin as code,
                            origin_name as name,
                            sum(amount) as total_land,
                            count(1) as total_hits
                        from
                            TownCrier
                        group by
                            origin
                        having
                            total_land > 0
                        order by
                            total_land desc;""")
        return self.db.session.execute(query)

    @property
    def abandons(self):
        query = text("""select
                            origin as code,
                            origin_name as name,
                            target as realm
                        from
                            TownCrier
                        where
                            event_type like 'abandon'
                        group by
                            realm;""")
        return self.db.session.execute(query)
