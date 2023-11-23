/* Backup all the data to history tables to improve performance */

DROP TABLE IF EXISTS ClearSight_History;
CREATE TABLE IF NOT EXISTS ClearSight_History (
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

DROP INDEX IF EXISTS idx_ClearSight_History;
CREATE UNIQUE INDEX idx_ClearSight_History ON ClearSight_History (dominion, timestamp);

DROP TRIGGER IF EXISTS Clearsight_Copy_History;
CREATE TRIGGER Clearsight_Copy_History
AFTER INSERT ON ClearSight
BEGIN
    INSERT INTO ClearSight_History
    VALUES (
            NEW.dominion,
            NEW.timestamp,
            NEW.land,
            NEW.peasants,
            NEW.networth,
            NEW.prestige,
            NEW.resource_platinum,
            NEW.resource_food,
            NEW.resource_mana,
            NEW.resource_ore,
            NEW.resource_gems,
            NEW.resource_boats,
            NEW.military_draftees,
            NEW.military_unit1,
            NEW.military_unit2,
            NEW.military_unit3,
            NEW.military_unit4,
            NEW.military_spies,
            NEW.military_assassins,
            NEW.military_wizards,
            NEW.military_archmages,
            NEW.clear_sight_accuracy
           );
END;

DROP TABLE IF EXISTS CastleSpy_History;
CREATE TABLE IF NOT EXISTS CastleSpy_History (
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

DROP INDEX IF EXISTS idx_CastleSpy_History;
CREATE UNIQUE INDEX idx_CastleSpy_History ON CastleSpy_History (dominion, timestamp);

DROP TRIGGER IF EXISTS CastleSpy_Copy_History;
CREATE TRIGGER CastleSpy_Copy_History
AFTER INSERT ON CastleSpy
BEGIN
    INSERT INTO CastleSpy_History
    VALUES (
            NEW.dominion,
            NEW.timestamp,
            NEW.science_points,
            NEW.science_rating,
            NEW.keep_points,
            NEW.keep_rating,
            NEW.spires_points,
            NEW.spires_rating,
            NEW.forges_points,
            NEW.forges_rating,
            NEW.walls_points,
            NEW.walls_rating,
            NEW.harbor_points,
            NEW.harbor_rating
           );
END;

DROP TABLE IF EXISTS BarracksSpy_History;
CREATE TABLE IF NOT EXISTS BarracksSpy_History (
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

DROP INDEX IF EXISTS idx_BarracksSpy_History;
CREATE UNIQUE INDEX idx_BarracksSpy_History ON BarracksSpy_History (dominion, timestamp);

DROP TRIGGER IF EXISTS BarracksSpy_Copy_History;
CREATE TRIGGER BarracksSpy_Copy_History
AFTER INSERT ON BarracksSpy
BEGIN
    INSERT INTO BarracksSpy_History
    VALUES (
            NEW.dominion,
            NEW.timestamp,
            NEW.draftees,
            NEW.home_unit1,
            NEW.home_unit2,
            NEW.home_unit3,
            NEW.home_unit4,
            NEW.training,
            NEW.return
           );
END;

DROP TABLE IF EXISTS SurveyDominion_History;
CREATE TABLE IF NOT EXISTS SurveyDominion_History (
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

DROP INDEX IF EXISTS idx_SurveyDominion_History;
CREATE UNIQUE INDEX idx_SurveyDominion_History ON SurveyDominion_History (dominion, timestamp);

DROP TRIGGER IF EXISTS SurveyDominion_Copy_History;
CREATE TRIGGER SurveyDominion_Copy_History
AFTER INSERT ON SurveyDominion
BEGIN
    INSERT INTO SurveyDominion_History
    VALUES (
            NEW.dominion,
            NEW.timestamp,
            NEW.home,
            NEW.alchemy,
            NEW.farm,
            NEW.smithy,
            NEW.masonry,
            NEW.ore_mine,
            NEW.gryphon_nest,
            NEW.tower,
            NEW.wizard_guild,
            NEW.temple,
            NEW.diamond_mine,
            NEW.school,
            NEW.lumberyard,
            NEW.forest_haven,
            NEW.factory,
            NEW.guard_tower,
            NEW.shrine,
            NEW.barracks,
            NEW.dock,
            NEW.constructing,
            NEW.barren_land,
            NEW.total_land
           );
END;

DROP TABLE IF EXISTS LandSpy_History;
CREATE TABLE IF NOT EXISTS LandSpy_History (
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

DROP INDEX IF EXISTS idx_LandSpy_History;
CREATE UNIQUE INDEX idx_LandSpy_History ON LandSpy_History (dominion, timestamp);

DROP TRIGGER IF EXISTS LandSpy_Copy_History;
CREATE TRIGGER LandSpy_Copy_History
AFTER INSERT ON LandSpy
BEGIN
    INSERT INTO LandSpy_History
    VALUES (
            NEW.dominion,
            NEW.timestamp,
            NEW.total,
            NEW.barren,
            NEW.constructed,
            NEW.plain,
            NEW.plain_constructed,
            NEW.mountain,
            NEW.mountain_constructed,
            NEW.swamp,
            NEW.swamp_constructed,
            NEW.cavern,
            NEW.cavern_constructed,
            NEW.forest,
            NEW.forest_constructed,
            NEW.hill,
            NEW.hill_constructed,
            NEW.water,
            NEW.water_constructed,
            NEW.incoming
           );
END;

INSERT INTO SchemaVersion (timestamp, version) VALUES (DATETIME('now'), '1.2');
