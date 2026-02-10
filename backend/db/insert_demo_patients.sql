-- DEMO PATIENTS with Comprehensive Medication Profiles - for Full Alert Spectrum Testing


-- DEMO PATIENT 1: "High-Risk Polypharmacy Patient" (ID: DEMO001)
-- Profile: Elderly patient on 8 medications with multiple drug-gene interactions
-- Genotype: Poor CYP2D6, Poor CYP2C19, Decreased SLCO1B1
-- Expected Alerts: Multiple RED/YELLOW alerts (high-risk profile)
-- Use Case: Demonstrates critical alerts requiring immediate action

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO001', 'CYP2D6', '*4', '*4', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO001', 'CYP2C19', '*2', '*2', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO001', 'SLCO1B1', '*5', '*5', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO001', 'ABCB1', '1236C>T', '1236C>T', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO001 (8 drugs - to be added via synthetic FHIR data):
-- 1. Codeine (CYP2D6 - RED alert: Poor metabolizer -> avoid)
-- 2. Clopidogrel (CYP2C19 - RED alert: Reduced efficacy)
-- 3. Simvastatin (SLCO1B1 - RED alert: High myopathy risk)
-- 4. Amitriptyline (CYP2D6 + CYP2C19 - RED alerts)
-- 5. Omeprazole (CYP2C19 - YELLOW alert)
-- 6. Metoprolol (CYP2D6 - YELLOW alert)
-- 7. Tramadol (CYP2D6 - RED alert)
-- 8. Venlafaxine (CYP2D6 - YELLOW alert)


-- DEMO PATIENT 2: "Ideal Candidate Profile" (ID: DEMO002)
-- Profile: Normal metabolizer across all genes (best-case scenario)
-- Genotype: Normal CYP2D6, Normal CYP2C19, Normal SLCO1B1
-- Expected Alerts: All GREEN alerts (standard dosing)
-- Use Case: Shows system working with optimal genomic profile

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO002', 'CYP2D6', '*1', '*1', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO002', 'CYP2C19', '*1', '*1', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO002', 'SLCO1B1', '*1A', '*1A', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO002', 'ABCB1', '1236C>C', '1236C>C', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO002 (6 drugs - all GREEN alerts):
-- 1. Codeine (GREEN)
-- 2. Clopidogrel (GREEN)
-- 3. Atorvastatin (GREEN)
-- 4. Citalopram (GREEN)
-- 5. Tramadol (GREEN)
-- 6. Omeprazole (GREEN)


-- DEMO PATIENT 3: "Ultrarapid Metabolizer" (ID: DEMO003)
-- Profile: Ultrarapid CYP2D6, Rapid CYP2C19 (opposite of poor metabolizer)
-- Genotype: Ultrarapid CYP2D6, Rapid CYP2C19, Normal SLCO1B1
-- Expected Alerts: RED/YELLOW for toxicity risk (faster drug activation)
-- Use Case: Shows less common but critical ultrarapid phenotype

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO003', 'CYP2D6', '*1/*2xN', '*1/*2xN', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO003', 'CYP2C19', '*17', '*17', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO003', 'SLCO1B1', '*1A', '*1A', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO003', 'ABCB1', '1236C>C', '1236C>C', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO003 (5 drugs - toxicity risk alerts):
-- 1. Codeine (RED: Ultrarapid -> high morphine levels -> toxicity risk)
-- 2. Tramadol (RED: Ultrarapid -> avoid)
-- 3. Citalopram (YELLOW: Rapid CYP2C19 -> may need higher dose)
-- 4. Omeprazole (YELLOW: Rapid -> reduced efficacy)
-- 5. Voriconazole (YELLOW: Rapid -> dose adjustment)


-- DEMO PATIENT 4: "Mixed Phenotype Profile" (ID: DEMO004)
-- Profile: Poor CYP2D6, Normal CYP2C19, Decreased SLCO1B1
-- Genotype: Mix of risk factors across different genes
-- Expected Alerts: RED for CYP2D6 drugs, GREEN for CYP2C19, YELLOW for statins
-- Use Case: Shows heterogeneous genomic profile

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO004', 'CYP2D6', '*4', '*5', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO004', 'CYP2C19', '*1', '*1', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO004', 'SLCO1B1', '*1A', '*15', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO004', 'ABCB1', '1236C>T', '1236T>T', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO004 (7 drugs - mixed alerts):
-- 1. Codeine (RED: Poor CYP2D6)
-- 2. Metoprolol (YELLOW: Poor CYP2D6 -> reduce dose 50%)
-- 3. Clopidogrel (GREEN: Normal CYP2C19)
-- 4. Citalopram (GREEN: Normal CYP2C19)
-- 5. Simvastatin (YELLOW: Decreased SLCO1B1 -> lower dose)
-- 6. Omeprazole (GREEN: Normal CYP2C19)
-- 7. Aripiprazole (YELLOW: Poor CYP2D6)


-- DEMO PATIENT 5: "Cardiovascular Polypharmacy" (ID: DEMO005)
-- Profile: Cardiac patient on multiple cardiovascular drugs
-- Genotype: Intermediate CYP2D6, Intermediate CYP2C19, Decreased SLCO1B1
-- Expected Alerts: YELLOW alerts for multiple cardiac medications
-- Use Case: Demonstrates common cardiovascular pharmacogenomic scenario

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO005', 'CYP2D6', '*1', '*4', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO005', 'CYP2C19', '*1', '*2', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO005', 'SLCO1B1', '*1A', '*5', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO005', 'ABCB1', '1236C>T', '1236C>T', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO005 (6 drugs - cardiovascular focus):
-- 1. Clopidogrel (YELLOW: Intermediate CYP2C19 -> reduced efficacy)
-- 2. Metoprolol (YELLOW: Intermediate CYP2D6 -> reduce dose)
-- 3. Atorvastatin (YELLOW: Decreased SLCO1B1 -> lower dose)
-- 4. Simvastatin (RED: Decreased SLCO1B1 -> avoid, use alternative)
-- 5. Carvedilol (YELLOW: Intermediate CYP2D6)
-- 6. Propranolol (YELLOW: Intermediate CYP2D6)


-- DEMO PATIENT 6: "Psychiatric Polypharmacy" (ID: DEMO006)
-- Profile: Mental health patient on multiple psychotropics
-- Genotype: Poor CYP2D6, Intermediate CYP2C19, Normal SLCO1B1
-- Expected Alerts: Multiple RED/YELLOW for antidepressants/antipsychotics
-- Use Case: Shows pharmacogenomic impact on psychiatric medications

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO006', 'CYP2D6', '*4', '*4', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO006', 'CYP2C19', '*1', '*2', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO006', 'SLCO1B1', '*1A', '*1A', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2, created_at)
VALUES ('DEMO006', 'ABCB1', '1236C>C', '1236C>C', NOW())
ON CONFLICT (patient_id, gene_symbol) DO UPDATE SET
    allele_1 = EXCLUDED.allele_1,
    allele_2 = EXCLUDED.allele_2,
    created_at = NOW();

-- Medications for DEMO006 (7 drugs - psychiatric focus):
-- 1. Amitriptyline (RED: Poor CYP2D6 + Intermediate CYP2C19)
-- 2. Venlafaxine (YELLOW: Poor CYP2D6 -> reduce dose)
-- 3. Paroxetine (YELLOW: Poor CYP2D6 -> reduce dose)
-- 4. Aripiprazole (YELLOW: Poor CYP2D6 -> reduce dose 50%)
-- 5. Risperidone (YELLOW: Poor CYP2D6 -> reduce dose)
-- 6. Citalopram (YELLOW: Intermediate CYP2C19)
-- 7. Atomoxetine (RED: Poor CYP2D6 -> reduce dose 50%)


-- Verification Query: Display all demo patients

SELECT 
    patient_id,
    gene_symbol,
    allele_1,
    allele_2,
    CASE 
        WHEN patient_id = 'DEMO001' THEN 'High-Risk Polypharmacy (8 meds)'
        WHEN patient_id = 'DEMO002' THEN 'Ideal Candidate (6 meds - all GREEN)'
        WHEN patient_id = 'DEMO003' THEN 'Ultrarapid Metabolizer (5 meds)'
        WHEN patient_id = 'DEMO004' THEN 'Mixed Phenotype (7 meds)'
        WHEN patient_id = 'DEMO005' THEN 'Cardiovascular Focus (6 meds)'
        WHEN patient_id = 'DEMO006' THEN 'Psychiatric Focus (7 meds)'
    END AS description
FROM genotypes
WHERE patient_id LIKE 'DEMO%'
ORDER BY patient_id, gene_symbol;

