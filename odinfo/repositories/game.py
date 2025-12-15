"""
Repository for game data access.

This module provides a clean interface for database operations,
hiding SQLAlchemy details from the rest of the application.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

from datetime import datetime

from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import Session

from odinfo.domain.models import (
    Dominion, TownCrier, ClearSight, BarracksSpy, CastleSpy,
    LandSpy, SurveyDominion, Vision, Revelation
)


logger = logging.getLogger('od-info.repository')


class GameRepository:
    """
    Repository for accessing game data.

    Provides a collection-like interface for Dominions and other game entities.
    Accepts a SQLAlchemy Session, making it work with both Flask-SQLAlchemy
    and standalone SQLAlchemy usage.
    """

    def __init__(self, session: Session):
        self._session = session

    @property
    def session(self) -> Session:
        """Expose session for cases where direct access is needed (e.g., commits)."""
        return self._session

    @contextmanager
    def transaction(self):
        """
        Context manager for grouping multiple operations in a single transaction.

        Auto-commits on success, rolls back on exception.

        Note: Most write methods (add_dominion, update_*, replace_*) already
        use this internally and auto-commit. Use this directly only when you
        need to group multiple reads and writes atomically.
        """
        try:
            yield
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    # ----------------------------- Dominion queries

    def all_dominions(self) -> Iterator[Dominion]:
        """Return all dominions."""
        return self._session.execute(select(Dominion)).scalars()

    def get_dominion(self, dom_id: int) -> Dominion | None:
        """Get a dominion by its code/id."""
        return self._session.execute(
            select(Dominion).where(Dominion.code == dom_id)
        ).scalar()

    def get_dominions_by_realm(self, realm_number: int) -> Iterator[Dominion]:
        """Get all dominions in a specific realm."""
        return self._session.execute(
            select(Dominion).where(Dominion.realm == realm_number)
        ).scalars()

    def get_realmies(self, dom_id: int) -> Iterator[Dominion]:
        """Get all dominions in the same realm as the given dominion."""
        dom = self.get_dominion(dom_id)
        if dom is None:
            raise ValueError(f"Dominion {dom_id} not found")
        return self.get_dominions_by_realm(dom.realm)

    def get_realm_of_dominion(self, dom_id: int) -> int:
        """Get the realm number for a dominion."""
        dom = self.get_dominion(dom_id)
        if dom is None:
            raise ValueError(f"Dominion {dom_id} not found")
        return dom.realm

    def add_dominion(self, dominion: Dominion) -> None:
        """Add a single dominion (auto-commits)."""
        with self.transaction():
            self._session.add(dominion)

    def add_dominions(self, dominions: list[Dominion]) -> None:
        """Add multiple dominions in a single transaction."""
        with self.transaction():
            self._session.add_all(dominions)

    def update_dominion_role(self, dom_id: int, role: str) -> None:
        """Update the role of a dominion."""
        with self.transaction():
            self._session.execute(
                update(Dominion).where(Dominion.code == dom_id).values(role=role)
            )

    def update_dominion_player(self, dom_id: int, player_name: str) -> None:
        """Update the player name of a dominion."""
        with self.transaction():
            self._session.execute(
                update(Dominion).where(Dominion.code == dom_id).values(player=player_name)
            )

    # ----------------------------- TownCrier queries

    def all_town_crier_events(self) -> Iterator[TownCrier]:
        """Return all town crier events."""
        return self._session.execute(select(TownCrier)).scalars()

    def replace_all_town_crier_events(self, events: list[TownCrier]) -> None:
        """
        Replace all town crier events with a new set.

        Deletes existing events and adds the new ones in a single transaction.
        """
        with self.transaction():
            self._session.query(TownCrier).delete()
            self._session.add_all(events)

    # ----------------------------- General utilities

    def is_empty(self) -> bool:
        """Check if the database has any dominions."""
        count = self._session.execute(
            select(func.count()).select_from(Dominion)
        ).scalar()
        is_empty = count == 0
        logger.debug(f'is_database_empty: {is_empty}')
        return is_empty

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()

    # ----------------------------- Ops cleanup

    def cleanup_old_ops(self, cutoff_time: datetime) -> dict[str, int]:
        """
        Delete ops entries older than cutoff_time.

        Preserves DominionHistory (for land/networth graphs) and TownCrier.
        Returns a dict mapping table name to number of deleted rows.
        """
        ops_tables = [
            ClearSight,
            BarracksSpy,
            CastleSpy,
            LandSpy,
            SurveyDominion,
            Vision,
            Revelation,
        ]

        deleted_counts = {}
        with self.transaction():
            for table in ops_tables:
                result = self._session.execute(
                    delete(table).where(table.timestamp < cutoff_time)
                )
                deleted_counts[table.__tablename__] = result.rowcount
                logger.info(f"Deleted {result.rowcount} rows from {table.__tablename__}")

        return deleted_counts

    def count_ops(self) -> dict[str, int]:
        """Count rows in each ops table."""
        ops_tables = [
            ClearSight,
            BarracksSpy,
            CastleSpy,
            LandSpy,
            SurveyDominion,
            Vision,
            Revelation,
        ]

        counts = {}
        for table in ops_tables:
            count = self._session.execute(
                select(func.count()).select_from(table)
            ).scalar()
            counts[table.__tablename__] = count

        return counts