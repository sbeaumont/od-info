import sys
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from odinfo.config import check_dirs_and_configs, load_secrets
from odinfo.facade.cache import FacadeCache
from odinfo.facade.odinfo import ODInfoFacade
from odinfo.repositories.game import GameRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("odinfo.cron")


def check_all_ok():
    """Check that the underlying file system is OK."""
    logging.info("Checking directories and config files...")
    problems = check_dirs_and_configs()
    if problems:
        logging.error('\n'.join(problems))
        sys.exit('\n'.join(problems))
    else:
        logger.info('All OK')


def initialize_database() -> GameRepository:
    """Initialize the database and return a repository."""
    db_url = load_secrets()['database_name']
    if db_url.startswith('sqlite'):
        db_url = db_url.replace('sqlite:///', 'sqlite:///instance/')
    logging.info("Initializing database")
    engine = create_engine(url=db_url,
                           pool_pre_ping=True,
                           pool_size=20,
                           max_overflow=10,
                           pool_timeout=10,
                           pool_recycle=280)
    session = Session(bind=engine)
    return GameRepository(session)


def update_all(repo: GameRepository) -> None:
    """Update all information from the OD into the database."""
    cache = FacadeCache()
    facade = ODInfoFacade(repo, cache)
    logging.info("Updating Dominions Index (from search page)...")
    facade.update_dom_index()
    logging.info("Updating all Dominions...")
    facade.update_all()
    logging.info("Updating realmies...")
    facade.update_realmies()


if __name__ == '__main__':
    check_all_ok()
    update_all(initialize_database())
