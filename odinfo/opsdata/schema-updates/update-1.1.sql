/* Add wpa column to deal with Icekin OP calc */
ALTER TABLE ClearSight ADD COLUMN wpa REAL;

INSERT INTO SchemaVersion (timestamp, version) VALUES (DATETIME('now'), '1.1');
