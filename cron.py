import sys
import logging

from sqlalchemy import create_engine, Engine, select
from sqlalchemy.orm import Session

from odinfo.config import check_dirs_and_configs, load_secrets
from odinfo.facade.odinfo import ODInfoFacade

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("odinfo.cron")


class EngineWrapper():
    def __init__(self, engine: Engine):
        self.engine = engine
        self._session = None

    @property
    def select(self):
        return select

    @property
    def session(self):
        if not self._session:
            self._session = Session(bind=self.engine)
        return self._session


def check_all_ok():
    """Check that the underlying file system is OK."""
    logging.info("Checking directories and config files...")
    problems = check_dirs_and_configs()
    if problems:
        logging.error('\n'.join(problems))
        sys.exit('\n'.join(problems))
    else:
        logger.info('All OK')


def initialize_database() -> EngineWrapper:
    """Initialize the database."""
    db_url = load_secrets()['database_name']
    if db_url.startswith('sqlite'):
        db_url = db_url.replace('sqlite:///', 'sqlite:///instance/')
    logging.info(f"Initializing database")
    engine = create_engine(url=db_url,
                           pool_pre_ping=True,
                           pool_size=20,
                           max_overflow=10,
                           pool_timeout=10,
                           pool_recycle=280)
    return EngineWrapper(engine)


def update_all(engine: EngineWrapper) -> None:
    """Update all information from the OD into the database."""
    cache = {}
    facade = ODInfoFacade(engine, cache)
    logging.info("Updating Dominions Index (from search page)...")
    facade.update_dom_index()
    logging.info("Updating all Dominions...")
    facade.update_all()
    logging.info("Updating realmies...")
    facade.update_realmies()


if __name__ == '__main__':
    check_all_ok()
    update_all(initialize_database())
