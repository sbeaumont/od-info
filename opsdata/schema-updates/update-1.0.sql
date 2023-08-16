CREATE TABLE IF NOT EXISTS SchemaVersion (
    timestamp DATETIME NOT NULL,
    version TEXT NOT NULL
);

INSERT INTO SchemaVersion (timestamp, version) VALUES (DATETIME('now'), '1.0');

DROP TABLE IF EXISTS Revelation;
CREATE TABLE IF NOT EXISTS Revelation (
    dominion  INTEGER  NOT NULL REFERENCES Dominions,
    timestamp DATETIME NOT NULL,
    spell TEXT NOT NULL,
    duration INTEGER NOT NULL,
    expires DATETIME NOT NULL
);

DROP INDEX IF EXISTS idx_Revelation;
CREATE UNIQUE INDEX idx_Revelation ON Revelation (dominion, timestamp, spell);

DROP TRIGGER IF EXISTS last_op_Revelation;
CREATE TRIGGER last_op_Revelation
AFTER INSERT ON Revelation
BEGIN
    UPDATE Dominions
    SET last_op = new.timestamp
    WHERE code = new.dominion
    AND (last_op < new.timestamp OR last_op IS NULL);
END;
