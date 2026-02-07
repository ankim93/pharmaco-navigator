"""
Data models for Clinical Decision Support alerts.
Defines Pydantic v2 schemas for drug-gene interaction recommendations and Traffic Light dashboard alerts.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, HttpUrl


# Alert Color Types (Traffic Light System)
AlertColor = Literal["RED", "YELLOW", "GREEN", "GREY"]


# DrugRecommendation Schema
class DrugRecommendation(BaseModel):
    """
    Clinical decision support alert for a single drug-gene interaction.
    """
    
    drug_name: str = Field(
        ...,
        description="Name of the medication",
        examples=["Codeine", "Clopidogrel", "Simvastatin"]
    )
    
    gene_symbol: str = Field(
        ...,
        description="Gene symbol involved in interaction",
        examples=["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]
    )
    
    phenotype: str = Field(
        ...,
        description="Patient's standardized CPIC phenotype",
        examples=[
            "Poor Metabolizer",
            "Intermediate Metabolizer",
            "Normal Metabolizer",
            "Poor Function",
            "Data Missing/Unknown"
        ]
    )
    
    alert_color: AlertColor = Field(
        ...,
        description="Traffic Light alert category"
    )
    
    clinical_action: str = Field(
        ...,
        description="Specific clinical recommendation text from CPIC",
        examples=[
            "Avoid codeine use; use alternative analgesic",
            "Consider alternative P2Y12 inhibitor (prasugrel, ticagrelor)",
            "Lower simvastatin dose (<40mg) or use alternative statin"
        ]
    )
    
    guideline_url: str = Field(
        ...,
        description="URL to full CPIC guideline"
    )
    
    classification: str = Field(
        default="Unspecified",
        description="Strength of recommendation (Strong, Moderate, Optional)"
    )
    
    guideline_level: str = Field(
        default="Unknown",
        description="CPIC evidence level (A or B)"
    )

    affected_medications: Optional[List[str]] = Field(
        default=None,
        description="List of patient's active medications affected by this gene"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "drug_name": "Codeine",
                    "gene_symbol": "CYP2D6",
                    "phenotype": "Poor Metabolizer",
                    "alert_color": "RED",
                    "clinical_action": "Avoid codeine use due to lack of efficacy; use alternative analgesic (e.g., morphine, hydromorphone)",
                    "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/",
                    "classification": "Strong",
                    "guideline_level": "A"
                },
                {
                    "drug_name": "Simvastatin",
                    "gene_symbol": "SLCO1B1",
                    "phenotype": "Decreased Function",
                    "alert_color": "YELLOW",
                    "clinical_action": "Lower simvastatin dose (<40mg daily) or consider alternative statin (pravastatin, rosuvastatin)",
                    "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-simvastatin-and-slco1b1/",
                    "classification": "Moderate",
                    "guideline_level": "A"
                },
                {
                    "drug_name": "Metformin",
                    "gene_symbol": "CYP2D6",
                    "phenotype": "Normal Metabolizer",
                    "alert_color": "GREEN",
                    "clinical_action": "No known pharmacogenomic interaction; use standard dosing",
                    "guideline_url": "https://cpicpgx.org/guidelines/",
                    "classification": "Standard",
                    "guideline_level": "Unknown"
                }
            ]
        }
    }


# Clinical Alert Response Schema
class ClinicalAlertResponse(BaseModel):
    """
    Complete clinical alert response for a patient with traffic light categorization.
    """
    
    patient_id: str = Field(
        ...,
        description="Patient identifier from FHIR context"
    )
    
    red_alerts: list[DrugRecommendation] = Field(
        default_factory=list,
        description="High-risk drug-gene interactions requiring immediate action"
    )
    
    yellow_alerts: list[DrugRecommendation] = Field(
        default_factory=list,
        description="Moderate-risk interactions requiring caution or monitoring"
    )
    
    green_alerts: list[DrugRecommendation] = Field(
        default_factory=list,
        description="No known pharmacogenomic interactions"
    )
    
    grey_alerts: list[DrugRecommendation] = Field(
        default_factory=list,
        description="Missing genomic data - unable to analyze"
    )

    active_medications: List[str] = Field(
        default_factory=list,
        description="All active medications for the patient"
    )
    
    total_medications: int = Field(
        default=0,
        description="Total number of medications analyzed",
        ge=0
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "patient_id": "12724067",
                    "red_alerts": [
                        {
                            "drug_name": "Codeine",
                            "gene_symbol": "CYP2D6",
                            "phenotype": "Poor Metabolizer",
                            "alert_color": "RED",
                            "clinical_action": "Avoid codeine use; use alternative analgesic",
                            "guideline_url": "https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/",
                            "classification": "Strong",
                            "guideline_level": "A"
                        }
                    ],
                    "yellow_alerts": [],
                    "green_alerts": [],
                    "grey_alerts": [],
                    "total_medications": 1
                }
            ]
        }
    }


# Genomic Profile Summary Schema
class GenomicProfileSummary(BaseModel):
    """
    Summary of patient's genomic profile for dashboard display.
    """
    
    patient_id: str = Field(
        ...,
        description="Patient identifier from FHIR context"
    )
    
    genes_analyzed: list[str] = Field(
        default_factory=list,
        description="Genes with available genomic data"
    )
    
    genes_missing: list[str] = Field(
        default_factory=list,
        description="Genes with missing genomic data"
    )
    
    phenotypes: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of gene symbol to standardized phenotype"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "patient_id": "12724067",
                    "genes_analyzed": ["CYP2D6", "CYP2C19"],
                    "genes_missing": ["SLCO1B1", "ABCB1"],
                    "phenotypes": {
                        "CYP2D6": "Poor Metabolizer",
                        "CYP2C19": "Normal Metabolizer",
                        "SLCO1B1": "Data Missing/Unknown",
                        "ABCB1": "Data Missing/Unknown"
                    }
                }
            ]
        }
    }
