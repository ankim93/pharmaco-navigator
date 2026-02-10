-- Reset genotypes table: wipe all data and restart auto-increment ID

DELETE FROM genotypes;

ALTER SEQUENCE genotypes_id_seq RESTART WITH 1;
