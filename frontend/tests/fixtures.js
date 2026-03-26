/**
 * Shared test fixtures for Pharmaco-Navigator frontend tests.
 */

// Single alert objects
export const redAlert = {
  drug_name: 'Codeine',
  gene_symbol: 'CYP2D6',
  phenotype: 'Poor Metabolizer',
  alert_color: 'RED',
  classification: 'Avoid Use',
  guideline_level: 'A',
  clinical_action:
    'Avoid codeine use due to lack of CYP2D6 enzyme activity. Risk of ineffective analgesia.',
  guideline_url: 'https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/',
  affected_medications: [],
};

export const yellowAlert = {
  drug_name: 'Clopidogrel',
  gene_symbol: 'CYP2C19',
  phenotype: 'Intermediate Metabolizer',
  alert_color: 'YELLOW',
  classification: 'Use with Caution',
  guideline_level: 'A',
  clinical_action:
    'Alternative antiplatelet therapy or increased monitoring recommended for intermediate metabolizers.',
  guideline_url: 'https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/',
  affected_medications: [],
};

export const greenAlert = {
  drug_name: 'Sertraline',
  gene_symbol: 'CYP2D6',
  phenotype: 'Normal Metabolizer',
  alert_color: 'GREEN',
  classification: 'Standard Dosing',
  guideline_level: 'A',
  clinical_action: 'Standard dosing recommended. Normal CYP2D6 enzyme activity.',
  guideline_url: 'https://cpicpgx.org/guidelines/guideline-for-ssri-and-cyp2d6-cyp2c19/',
  affected_medications: [],
};

export const greyAlert = {
  drug_name: 'Tacrolimus',
  gene_symbol: 'ABCB1',
  phenotype: 'Data Missing/Unknown',
  alert_color: 'GREY',
  classification: 'No CPIC Level A/B Guidelines',
  guideline_level: 'N/A',
  clinical_action: 'No CPIC Level A/B guideline available for this gene-drug pair.',
  guideline_url: '',
  affected_medications: ['Tacrolimus'],
};

// Full API response payloads

/** Patient with all risk levels present — covers the typical use case. */
export const fullAlertResponse = {
  patient_id: 'DEMO001',
  total_medications: 4,
  active_medications: ['Codeine', 'Clopidogrel', 'Sertraline', 'Tacrolimus'],
  red_alerts: [redAlert],
  yellow_alerts: [yellowAlert],
  green_alerts: [greenAlert],
  grey_alerts: [greyAlert],
};

/** Patient with no high-risk alerts — tests empty column messages. */
export const safePatientResponse = {
  patient_id: 'DEMO002',
  total_medications: 1,
  active_medications: ['Sertraline'],
  red_alerts: [],
  yellow_alerts: [],
  green_alerts: [greenAlert],
  grey_alerts: [],
};

/** Patient with only red alerts — maximum risk scenario. */
export const highRiskPatientResponse = {
  patient_id: 'DEMO003',
  total_medications: 1,
  active_medications: ['Codeine'],
  red_alerts: [redAlert],
  yellow_alerts: [],
  green_alerts: [],
  grey_alerts: [],
};

/** Empty response — no data scenario. */
export const emptyAlertResponse = {
  patient_id: 'UNKNOWN',
  total_medications: 0,
  active_medications: [],
  red_alerts: [],
  yellow_alerts: [],
  green_alerts: [],
  grey_alerts: [],
};

// Gene summary (derived from fullAlertResponse)
export const geneSummary = {
  CYP2D6: { phenotype: 'Poor Metabolizer', red: 1, yellow: 0, green: 1 },
  CYP2C19: { phenotype: 'Intermediate Metabolizer', red: 0, yellow: 1, green: 0 },
  ABCB1: { phenotype: 'Data Missing/Unknown', red: 0, yellow: 0, green: 0, hasGuidelines: false },
};
