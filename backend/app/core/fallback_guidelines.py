"""
Fallback CPIC Guidelines for offline operation.
Provides local backup of Level A/B drug-gene recommendations when the CPIC API is unavailable.
"""

from typing import Dict, List, Any


# CYP2D6 Guidelines (Level A)
CYP2D6_GUIDELINES: Dict[str, List[Dict[str, Any]]] = {
    "Poor Metabolizer": [
        {
            "drugname": "Codeine",
            "recommendation": "Avoid codeine use due to lack of efficacy; use alternative analgesic (e.g., morphine, hydromorphone, oxycodone - not tramadol)",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Tramadol",
            "recommendation": "Avoid tramadol use due to lack of efficacy; use alternative analgesic (e.g., morphine, hydromorphone, oxycodone - not codeine)",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tramadol-and-cyp2d6/"
            }
        },
        {
            "drugname": "Amitriptyline",
            "recommendation": "Consider alternative drug not predominantly metabolized by CYP2D6. If amitriptyline is warranted, consider 50% reduction of recommended starting dose and titrate to response or use therapeutic drug monitoring to guide dose adjustments.",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tricyclic-antidepressants-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Venlafaxine",
            "recommendation": "Consider 50% reduction of recommended starting dose. Titrate to response or use therapeutic drug monitoring to guide dose adjustments.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-venlafaxine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Paroxetine",
            "recommendation": "Consider 50% reduction of recommended starting dose and titrate to response or select alternative drug not predominantly metabolized by CYP2D6.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Metoprolol",
            "recommendation": "Consider 50-75% reduction of recommended starting dose. Monitor heart rate and blood pressure. Alternatively, consider non-CYP2D6 metabolized beta-blocker (e.g., atenolol, bisoprolol).",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Aripiprazole",
            "recommendation": "Reduce aripiprazole dose to 50% of usual recommended dose. Monitor closely for adverse effects.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-aripiprazole-and-cyp2d6/"
            }
        },
        {
            "drugname": "Risperidone",
            "recommendation": "Consider 50% reduction of recommended starting dose and titrate to response. Monitor for adverse effects including extrapyramidal symptoms.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-risperidone-and-cyp2d6/"
            }
        },
        {
            "drugname": "Atomoxetine",
            "recommendation": "Reduce dose to 50% of target dose and adjust based on response and tolerability. Monitor for increased adverse effects.",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-atomoxetine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Carvedilol",
            "recommendation": "Consider 50% reduction of recommended starting dose. Monitor heart rate and blood pressure closely.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Propranolol",
            "recommendation": "Consider 25-50% reduction of recommended starting dose. Monitor heart rate and blood pressure.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        }
    ],
    "Intermediate Metabolizer": [
        {
            "drugname": "Codeine",
            "recommendation": "Use alternative analgesic with better efficacy profile (e.g., morphine, oxycodone - not tramadol). If codeine is used, monitor closely for lack of efficacy.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Tramadol",
            "recommendation": "Use alternative analgesic with better efficacy profile (e.g., morphine, oxycodone - not codeine). If tramadol is used, monitor closely for lack of efficacy.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tramadol-and-cyp2d6/"
            }
        },
        {
            "drugname": "Amitriptyline",
            "recommendation": "Consider 25% reduction of recommended starting dose and titrate to response or use therapeutic drug monitoring to guide dose adjustments.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tricyclic-antidepressants-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Venlafaxine",
            "recommendation": "Consider 25-50% reduction of recommended starting dose and titrate to response.",
            "classification": "Optional",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-venlafaxine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Paroxetine",
            "recommendation": "Consider 25-50% reduction of recommended starting dose and titrate to response.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Metoprolol",
            "recommendation": "Consider 25-50% reduction of recommended starting dose and titrate to response. Monitor heart rate and blood pressure.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Aripiprazole",
            "recommendation": "Consider 25% dose reduction and monitor for adverse effects.",
            "classification": "Optional",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-aripiprazole-and-cyp2d6/"
            }
        },
        {
            "drugname": "Risperidone",
            "recommendation": "Consider 25% reduction of recommended starting dose and titrate to response.",
            "classification": "Optional",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-risperidone-and-cyp2d6/"
            }
        },
        {
            "drugname": "Atomoxetine",
            "recommendation": "Consider dose reduction to 75% of target dose based on response and tolerability.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-atomoxetine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Carvedilol",
            "recommendation": "Consider 25% reduction of recommended starting dose and monitor response.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Propranolol",
            "recommendation": "Initiate therapy at recommended starting dose and monitor response.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        }
    ],
    "Normal Metabolizer": [
        {
            "drugname": "Codeine",
            "recommendation": "Use label-recommended age- or weight-specific dosing.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Tramadol",
            "recommendation": "Use label-recommended age- or weight-specific dosing.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tramadol-and-cyp2d6/"
            }
        },
        {
            "drugname": "Amitriptyline",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tricyclic-antidepressants-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Venlafaxine",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-venlafaxine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Paroxetine",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Metoprolol",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Aripiprazole",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-aripiprazole-and-cyp2d6/"
            }
        },
        {
            "drugname": "Risperidone",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-risperidone-and-cyp2d6/"
            }
        },
        {
            "drugname": "Atomoxetine",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-atomoxetine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Carvedilol",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Propranolol",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        }
    ],
    "Ultrarapid Metabolizer": [
        {
            "drugname": "Codeine",
            "recommendation": "Avoid codeine use due to potential for toxicity; use alternative analgesic (e.g., morphine, oxycodone - not tramadol).",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Tramadol",
            "recommendation": "Avoid tramadol use due to potential for toxicity; use alternative analgesic (e.g., morphine, oxycodone - not codeine).",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tramadol-and-cyp2d6/"
            }
        },
        {
            "drugname": "Amitriptyline",
            "recommendation": "Avoid tertiary amines (amitriptyline); consider alternative drug (e.g., sertraline, citalopram) or monitor closely for lack of efficacy if amitriptyline is used.",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-tricyclic-antidepressants-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Venlafaxine",
            "recommendation": "Monitor closely for lack of efficacy. Consider alternative drug not predominantly metabolized by CYP2D6 or increase dose if needed.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-venlafaxine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Paroxetine",
            "recommendation": "Monitor for lack of efficacy. Consider alternative drug not predominantly metabolized by CYP2D6.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Metoprolol",
            "recommendation": "Monitor for lack of efficacy. Consider increased dose or alternative beta-blocker not metabolized by CYP2D6.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Aripiprazole",
            "recommendation": "Monitor for lack of efficacy. Consider dose increase if clinically appropriate.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-aripiprazole-and-cyp2d6/"
            }
        },
        {
            "drugname": "Risperidone",
            "recommendation": "Monitor for lack of efficacy. Consider alternative antipsychotic or dose adjustment.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-risperidone-and-cyp2d6/"
            }
        },
        {
            "drugname": "Atomoxetine",
            "recommendation": "Monitor for lack of efficacy. May require higher doses to achieve therapeutic effect.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-atomoxetine-and-cyp2d6/"
            }
        },
        {
            "drugname": "Carvedilol",
            "recommendation": "Monitor for lack of efficacy. Consider increased dose if clinically indicated.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        },
        {
            "drugname": "Propranolol",
            "recommendation": "Monitor for lack of efficacy. Consider increased dose if needed.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-beta-blockers-and-cyp2d6/"
            }
        }
    ]
}


# CYP2C19 Guidelines (Level A/B)
CYP2C19_GUIDELINES: Dict[str, List[Dict[str, Any]]] = {
    "Poor Metabolizer": [
        {
            "drugname": "Clopidogrel",
            "recommendation": "Alternative antiplatelet therapy (e.g., prasugrel, ticagrelor) is recommended due to reduced platelet inhibition and increased risk of cardiovascular events.",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/"
            }
        },
        {
            "drugname": "Escitalopram",
            "recommendation": "Consider 50% reduction of recommended starting dose and titrate to response, or select alternative drug not predominantly metabolized by CYP2C19.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Citalopram",
            "recommendation": "Consider 50% reduction of recommended starting dose and titrate to response, or select alternative drug not predominantly metabolized by CYP2C19.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Omeprazole",
            "recommendation": "Initiate therapy at standard dose. Consider dose reduction based on clinical response.",
            "classification": "Optional",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-proton-pump-inhibitors-and-cyp2c19/"
            }
        },
        {
            "drugname": "Voriconazole",
            "recommendation": "Choose alternative agent not metabolized by CYP2C19 or reduce maintenance dose by 50% and monitor voriconazole concentrations closely.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-voriconazole-and-cyp2c19/"
            }
        }
    ],
    "Intermediate Metabolizer": [
        {
            "drugname": "Clopidogrel",
            "recommendation": "Alternative antiplatelet therapy (e.g., prasugrel, ticagrelor) is recommended particularly in patients with acute coronary syndrome or undergoing PCI.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/"
            }
        },
        {
            "drugname": "Escitalopram",
            "recommendation": "Consider 25-50% reduction of recommended starting dose and titrate to response.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Citalopram",
            "recommendation": "Consider 25-50% reduction of recommended starting dose and titrate to response.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Omeprazole",
            "recommendation": "Initiate therapy at standard dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-proton-pump-inhibitors-and-cyp2c19/"
            }
        },
        {
            "drugname": "Voriconazole",
            "recommendation": "Initiate with standard dose and monitor voriconazole concentrations. Consider dose reduction if levels are elevated.",
            "classification": "Optional",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-voriconazole-and-cyp2c19/"
            }
        }
    ],
    "Normal Metabolizer": [
        {
            "drugname": "Clopidogrel",
            "recommendation": "Use label-recommended dosage.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/"
            }
        },
        {
            "drugname": "Escitalopram",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Citalopram",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Omeprazole",
            "recommendation": "Initiate therapy at standard dose.",
            "classification": "Standard",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-proton-pump-inhibitors-and-cyp2c19/"
            }
        },
        {
            "drugname": "Voriconazole",
            "recommendation": "Initiate therapy with recommended starting dose.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-voriconazole-and-cyp2c19/"
            }
        }
    ],
    "Ultrarapid Metabolizer": [
        {
            "drugname": "Clopidogrel",
            "recommendation": "Use label-recommended dosage.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-clopidogrel-and-cyp2c19/"
            }
        },
        {
            "drugname": "Escitalopram",
            "recommendation": "Consider alternative drug not predominantly metabolized by CYP2C19. If escitalopram is warranted, initiate at recommended dose and monitor for lack of efficacy.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Citalopram",
            "recommendation": "Consider alternative drug not predominantly metabolized by CYP2C19. If citalopram is warranted, initiate at recommended dose and monitor for lack of efficacy.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-selective-serotonin-reuptake-inhibitors-and-cyp2d6-and-cyp2c19/"
            }
        },
        {
            "drugname": "Omeprazole",
            "recommendation": "Consider alternative PPI (e.g., esomeprazole, pantoprazole) or increase dose. Monitor for lack of efficacy.",
            "classification": "Moderate",
            "guideline": {
                "level": "B",
                "url": "https://cpicpgx.org/guidelines/guideline-for-proton-pump-inhibitors-and-cyp2c19/"
            }
        },
        {
            "drugname": "Voriconazole",
            "recommendation": "Increase maintenance dose by 100-200% or choose alternative agent. Monitor voriconazole concentrations to ensure therapeutic levels.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-voriconazole-and-cyp2c19/"
            }
        }
    ]
}


# SLCO1B1 Guidelines (Level A)
SLCO1B1_GUIDELINES: Dict[str, List[Dict[str, Any]]] = {
    "Poor Function": [
        {
            "drugname": "Simvastatin",
            "recommendation": "Prescribe alternative statin (e.g., pravastatin, rosuvastatin) or lower simvastatin dose (≤20mg daily) and monitor closely for myopathy/rhabdomyolysis (16-fold increased risk).",
            "classification": "Strong",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        },
        {
            "drugname": "Atorvastatin",
            "recommendation": "Consider lower dose or alternative statin (e.g., pravastatin, rosuvastatin). Monitor closely for myopathy.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        }
    ],
    "Decreased Function": [
        {
            "drugname": "Simvastatin",
            "recommendation": "Lower simvastatin dose (≤40mg daily) or prescribe alternative statin (e.g., pravastatin, rosuvastatin). Monitor for myopathy (4-fold increased risk).",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        },
        {
            "drugname": "Atorvastatin",
            "recommendation": "Consider lower dose or monitor closely for myopathy.",
            "classification": "Moderate",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        }
    ],
    "Normal Function": [
        {
            "drugname": "Simvastatin",
            "recommendation": "Use label-recommended dosage and administration.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        },
        {
            "drugname": "Atorvastatin",
            "recommendation": "Use label-recommended dosage and administration.",
            "classification": "Standard",
            "guideline": {
                "level": "A",
                "url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/"
            }
        }
    ]
}


# ABCB1 Guidelines
ABCB1_GUIDELINES: Dict[str, List[Dict[str, Any]]] = {}


# Unified Fallback Registry
FALLBACK_GUIDELINES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "CYP2D6": CYP2D6_GUIDELINES,
    "CYP2C19": CYP2C19_GUIDELINES,
    "SLCO1B1": SLCO1B1_GUIDELINES,
    "ABCB1": ABCB1_GUIDELINES,
}


# Fallback Query Function
def get_fallback_recommendations(gene: str, phenotype: str) -> List[Dict[str, Any]]:
    """
    Retrieve fallback CPIC recommendations for a gene-phenotype pair.
    """
    if gene not in FALLBACK_GUIDELINES:
        return []
    
    gene_guidelines = FALLBACK_GUIDELINES[gene]
    
    if phenotype not in gene_guidelines:
        return []
    
    return gene_guidelines[phenotype]


def is_fallback_available(gene: str) -> bool:
    """
    Check if fallback guidelines are available for a gene.
    """
    return gene in FALLBACK_GUIDELINES and len(FALLBACK_GUIDELINES[gene]) > 0
