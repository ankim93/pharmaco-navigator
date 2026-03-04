"""
Insert genomic data for all Cerner sandbox patients into Azure PostgreSQL.
Covers 9 patients with varied pharmacogenomic profiles for testing.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _phenotype(gene: str, allele1: str, allele2: str) -> str:
    if gene == "CYP2D6":
        if "xN" in allele1 or "xN" in allele2:
            return "Ultrarapid Metabolizer (UM)"
        if allele1 == "*4" and allele2 == "*4":
            return "Poor Metabolizer (PM)"
        if "*4" in (allele1, allele2):
            return "Intermediate Metabolizer (IM)"
        if allele1 in ("*1", "*2") and allele2 in ("*1", "*2"):
            return "Normal Metabolizer (NM)"
    elif gene == "CYP2C19":
        if "*2" in (allele1, allele2):
            return "Poor Metabolizer (PM)"
        if allele1 == "*17" and allele2 == "*17":
            return "Ultrarapid Metabolizer (UM)"
        if "*17" in (allele1, allele2):
            return "Rapid Metabolizer (RM)"
        if allele1 == "*1" and allele2 == "*1":
            return "Normal Metabolizer (NM)"
    elif gene == "SLCO1B1":
        if "*5" in (allele1, allele2) or "*15" in (allele1, allele2):
            return "Decreased Function"
        return "Normal Function"
    return ""


def insert_cerner_patients() -> None:
    """
    Insert genomic data for all Cerner sandbox test patients.
    """

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not found in backend/.env")
        return

    # All Cerner sandbox patients with pharmacogenomic profiles.
    patients = [
        # 12724065 - Poor CYP2D6 & CYP2C19 -> RED for Codeine + Clopidogrel
        ("12724065", "CYP2D6",   "*4",      "*4"),
        ("12724065", "CYP2C19",  "*2",      "*2"),
        ("12724065", "SLCO1B1",  "*1A",     "*1A"),
        ("12724065", "ABCB1",    "1236C>T", "1236C>T"),

        # 12724069 - Intermediate CYP2D6, Decreased SLCO1B1 -> YELLOW
        ("12724069", "CYP2D6",   "*1",      "*4"),
        ("12724069", "CYP2C19",  "*1",      "*1"),
        ("12724069", "SLCO1B1",  "*1A",     "*5"),
        ("12724069", "ABCB1",    "1236C>T", "3435C>T"),

        # 12724066 - Normal CYP2D6, Rapid CYP2C19 -> mostly GREEN
        ("12724066", "CYP2D6",   "*1",      "*1"),
        ("12724066", "CYP2C19",  "*1",      "*17"),
        ("12724066", "SLCO1B1",  "*1A",     "*1A"),
        ("12724066", "ABCB1",    "1236C>C", "1236C>C"),

        # 12724067 - Poor CYP2D6, Decreased SLCO1B1 -> RED for Codeine + statins
        ("12724067", "CYP2D6",   "*4",      "*4"),
        ("12724067", "CYP2C19",  "*1",      "*1"),
        ("12724067", "SLCO1B1",  "*5",      "*5"),
        ("12724067", "ABCB1",    "1236C>T", "1236C>T"),

        # 12724068 - Ultrarapid CYP2D6 -> RED for Codeine (toxicity risk)
        ("12724068", "CYP2D6",   "*1",      "*2xN"),
        ("12724068", "CYP2C19",  "*1",      "*1"),
        ("12724068", "SLCO1B1",  "*1A",     "*1A"),
        ("12724068", "ABCB1",    "1236C>C", "3435C>T"),

        # 12724070 - Normal across all genes -> GREEN (ideal baseline patient)
        ("12724070", "CYP2D6",   "*1",      "*1"),
        ("12724070", "CYP2C19",  "*1",      "*1"),
        ("12724070", "SLCO1B1",  "*1A",     "*1A"),
        ("12724070", "ABCB1",    "1236C>T", "3435C>T"),

        # 12724071 - Ultrarapid CYP2C19, Decreased SLCO1B1 -> YELLOW/RED for statins
        ("12724071", "CYP2D6",   "*1",      "*1"),
        ("12724071", "CYP2C19",  "*17",     "*17"),
        ("12724071", "SLCO1B1",  "*5",      "*15"),
        ("12724071", "ABCB1",    "1236C>T", "1236C>T"),

        # 12742571 - Normal Metabolizer 
        ("12742571", "CYP2D6",   "*1",      "*1"),
        ("12742571", "CYP2C19",  "*1",      "*1"),
        ("12742571", "SLCO1B1",  "*1A",     "*1A"),
        ("12742571", "ABCB1",    "1236C>T", "3435C>T"),

        # 12742400 - Ultrarapid CYP2D6 & CYP2C19 
        ("12742400", "CYP2D6",   "*1/*2xN", "*1/*2xN"),
        ("12742400", "CYP2C19",  "*17",     "*17"),
        ("12742400", "SLCO1B1",  "*1A",     "*1B"),
        ("12742400", "ABCB1",    "1236C>T", "1236C>C"),
    ]

    print("Connecting to Azure PostgreSQL...")
    try:
        conn = psycopg2.connect(database_url)
        print("Connected successfully")
    except Exception as e:
        print(f"ERROR: Could not connect — {e}")
        print("\nTroubleshooting:")
        print("  1. Check DATABASE_URL in backend/.env")
        print("  2. Verify Azure PostgreSQL firewall allows your IP")
        print("  3. Confirm database credentials are correct")
        return

    print(f"\nInserting genomic data for all Cerner patients ({len(patients)} records)...\n")

    cursor = conn.cursor()
    inserted = 0
    current_patient = None

    for patient_id, gene, allele1, allele2 in patients:
        if patient_id != current_patient:
            if current_patient is not None:
                print()
            current_patient = patient_id
            print(f"Patient {patient_id}:")

        try:
            cursor.execute(
                """
                INSERT INTO genotypes (patient_id, gene_symbol, allele_1, allele_2)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (patient_id, gene_symbol)
                DO UPDATE SET
                    allele_1 = EXCLUDED.allele_1,
                    allele_2 = EXCLUDED.allele_2
                """,
                (patient_id, gene, allele1, allele2),
            )
            phenotype = _phenotype(gene, allele1, allele2)
            print(f"  {gene:10} {allele1:12}/{allele2:12}  {phenotype}")
            inserted += 1
        except Exception as e:
            print(f"  {gene}: ERROR — {e}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n{'='*70}")
    print(f"SUCCESS: Inserted {inserted} genotype records for all Cerner patients")
    print(f"{'='*70}")
    print("\nTest patients in Cerner sandbox:")
    print("  12724065 -> RED alerts (Poor CYP2D6 + CYP2C19)")
    print("  12724068 -> RED alerts (Ultrarapid CYP2D6 — toxicity risk)")
    print("  12724069 -> YELLOW alerts (Intermediate CYP2D6)")
    print("  12724070 -> GREEN alerts (Normal — ideal baseline)")
    print("  12724071 -> YELLOW/RED (Ultrarapid CYP2C19, statin risk)")


if __name__ == "__main__":
    print("=" * 70)
    print("  CERNER SANDBOX — GENOMIC DATA INSERTION")
    print("=" * 70)
    print()
    insert_cerner_patients()
