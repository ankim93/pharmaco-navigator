-- Pharmaco Navigator — initial schema

CREATE TABLE IF NOT EXISTS genotypes (
    id          SERIAL PRIMARY KEY,
    patient_id  VARCHAR(255)  NOT NULL,
    gene_symbol VARCHAR(50)   NOT NULL,
    allele_1    VARCHAR(50)   NOT NULL,
    allele_2    VARCHAR(50)   NOT NULL,
    created_at  TIMESTAMP,
    CONSTRAINT uq_genotype_patient_gene UNIQUE (patient_id, gene_symbol)
);

CREATE INDEX IF NOT EXISTS ix_genotypes_patient_id  ON genotypes (patient_id);
CREATE INDEX IF NOT EXISTS ix_genotypes_gene_symbol ON genotypes (gene_symbol);
