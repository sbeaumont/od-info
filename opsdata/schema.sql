DROP TABLE IF EXISTS Dominions;

CREATE TABLE IF NOT EXISTS Dominions (
	code INTEGER PRIMARY KEY,
   	name TEXT NOT NULL,
	realm INTEGER NOT NULL,
	race TEXT NOT NULL,
	player TEXT DEFAULT '?',
	role TEXT CHECK(role IN ('attacker', 'explorer', 'blopper', 'unknown', 'abandoner')) DEFAULT 'unknown',
	last_op DATETIME
);

DROP TABLE IF EXISTS DominionHistory;

CREATE TABLE IF NOT EXISTS DominionHistory (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    land      INTEGER  NOT NULL,
    networth  INTEGER  NOT NULL,
    timestamp DATETIME NOT NULL
);

DROP INDEX IF EXISTS idx_DominionHistory;
CREATE UNIQUE INDEX idx_DominionHistory ON DominionHistory (dominion, timestamp);

DROP TABLE IF EXISTS ClearSight;

CREATE TABLE IF NOT EXISTS ClearSight (
    dominion INTEGER NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    land INTEGER NOT NULL,
    peasants INTEGER NOT NULL,
    networth INTEGER NOT NULL,
    prestige INTEGER NOT NULL,
    resource_platinum INTEGER NOT NULL,
    resource_food INTEGER NOT NULL,
    resource_mana INTEGER NOT NULL,
    resource_ore INTEGER NOT NULL,
    resource_gems INTEGER NOT NULL,
    resource_boats INTEGER NOT NULL,
    military_draftees INTEGER NOT NULL,
    military_unit1 INTEGER NOT NULL,
    military_unit2 INTEGER NOT NULL,
    military_unit3 INTEGER NOT NULL,
    military_unit4 INTEGER NOT NULL,
    military_spies INTEGER,
    military_assassins INTEGER,
    military_wizards INTEGER,
    military_archmages INTEGER,
    clear_sight_accuracy REAL DEFAULT 0.85
);

DROP INDEX IF EXISTS idx_ClearSight;
CREATE UNIQUE INDEX idx_ClearSight ON ClearSight (dominion, timestamp);

DROP TRIGGER IF EXISTS last_op_Clearsight;
CREATE TRIGGER last_op_Clearsight
AFTER INSERT ON ClearSight
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS CastleSpy;

CREATE TABLE IF NOT EXISTS CastleSpy (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    science_points INTEGER NOT NULL,
    science_rating REAL NOT NULL,
    keep_points INTEGER NOT NULL,
    keep_rating REAL NOT NULL,
    spires_points INTEGER NOT NULL,
    spires_rating REAL NOT NULL,
    forges_points INTEGER NOT NULL,
    forges_rating REAL NOT NULL,
    walls_points INTEGER NOT NULL,
    walls_rating REAL NOT NULL,
    harbor_points INTEGER NOT NULL,
    harbor_rating REAL NOT NULL
);

DROP INDEX IF EXISTS idx_CastleSpy;
CREATE UNIQUE INDEX idx_CastleSpy ON CastleSpy (dominion, timestamp);

DROP TRIGGER IF EXISTS last_op_CastleSpy;
CREATE TRIGGER last_op_CastleSpy
AFTER INSERT ON CastleSpy
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS BarracksSpy;

CREATE TABLE IF NOT EXISTS BarracksSpy (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    draftees   INTEGER NOT NULL DEFAULT 0,
    home_unit1 INTEGER NOT NULL DEFAULT 0,
    home_unit2 INTEGER NOT NULL DEFAULT 0,
    home_unit3 INTEGER NOT NULL DEFAULT 0,
    home_unit4 INTEGER NOT NULL DEFAULT 0,
    training TEXT,
    return TEXT
);

DROP INDEX IF EXISTS idx_BarracksSpy;
CREATE UNIQUE INDEX idx_BarracksSpy ON BarracksSpy (dominion, timestamp);

DROP TRIGGER IF EXISTS last_op_BarracksSpy;
CREATE TRIGGER last_op_BarracksSpy
AFTER INSERT ON BarracksSpy
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS SurveyDominion;

CREATE TABLE IF NOT EXISTS SurveyDominion (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    home INTEGER NOT NULL,
    alchemy INTEGER NOT NULL DEFAULT 0,
    farm INTEGER NOT NULL DEFAULT 0,
    smithy INTEGER NOT NULL DEFAULT 0,
    masonry INTEGER NOT NULL DEFAULT 0,
    ore_mine INTEGER NOT NULL DEFAULT 0,
    gryphon_nest INTEGER NOT NULL DEFAULT 0,
    tower INTEGER NOT NULL DEFAULT 0,
    wizard_guild INTEGER NOT NULL DEFAULT 0,
    temple INTEGER NOT NULL DEFAULT 0,
    diamond_mine INTEGER NOT NULL DEFAULT 0,
    school INTEGER NOT NULL DEFAULT 0,
    lumberyard INTEGER NOT NULL DEFAULT 0,
    forest_haven INTEGER NOT NULL DEFAULT 0,
    factory INTEGER NOT NULL DEFAULT 0,
    guard_tower INTEGER NOT NULL DEFAULT 0,
    shrine INTEGER NOT NULL DEFAULT 0,
    barracks INTEGER NOT NULL DEFAULT 0,
    dock INTEGER NOT NULL DEFAULT 0,
    constructing TEXT,
    barren_land INTEGER NOT NULL DEFAULT 0,
    total_land INTEGER NOT NULL DEFAULT 0
);

DROP INDEX IF EXISTS idx_SurveyDominion;
CREATE UNIQUE INDEX idx_SurveyDominion ON SurveyDominion (dominion, timestamp);

DROP TRIGGER IF EXISTS last_op_SurveyDominion;
CREATE TRIGGER last_op_SurveyDominion
AFTER INSERT ON SurveyDominion
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS LandSpy;

CREATE TABLE IF NOT EXISTS LandSpy (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    total INTEGER NOT NULL DEFAULT 0,
    barren INTEGER NOT NULL DEFAULT 0,
    constructed INTEGER NOT NULL DEFAULT 0,
    plain INTEGER NOT NULL DEFAULT 0,
    plain_constructed INTEGER NOT NULL DEFAULT 0,
    mountain INTEGER NOT NULL DEFAULT 0,
    mountain_constructed INTEGER NOT NULL DEFAULT 0,
    swamp INTEGER NOT NULL DEFAULT 0,
    swamp_constructed INTEGER NOT NULL DEFAULT 0,
    cavern INTEGER NOT NULL DEFAULT 0,
    cavern_constructed INTEGER NOT NULL DEFAULT 0,
    forest INTEGER NOT NULL DEFAULT 0,
    forest_constructed INTEGER NOT NULL DEFAULT 0,
    hill INTEGER NOT NULL DEFAULT 0,
    hill_constructed INTEGER NOT NULL DEFAULT 0,
    water INTEGER NOT NULL DEFAULT 0,
    water_constructed INTEGER NOT NULL DEFAULT 0,
    incoming TEXT
);

DROP INDEX IF EXISTS idx_LandSpy;
CREATE UNIQUE INDEX idx_LandSpy ON LandSpy (dominion, timestamp);

DROP TRIGGER IF EXISTS last_op_LandSpy;
CREATE TRIGGER last_op_LandSpy
AFTER INSERT ON LandSpy
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS Vision;
CREATE TABLE IF NOT EXISTS Vision (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    techs TEXT NOT NULL
);

DROP TRIGGER IF EXISTS last_op_Vision;
CREATE TRIGGER last_op_Vision
AFTER INSERT ON Vision
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;

DROP TABLE IF EXISTS TownCrier;

CREATE TABLE IF NOT EXISTS TownCrier (
    timestamp DATETIME NOT NULL,
    origin INTEGER NOT NULL,
    origin_name TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'other',
    target INTEGER NOT NULL,
    target_name TEXT NOT NULL,
    amount INTEGER DEFAULT 0,
    text TEXT NOT NULL
);

DROP INDEX IF EXISTS idx_TownCrier;
CREATE UNIQUE INDEX idx_TownCrier ON TownCrier (timestamp, origin, event_type, target);
