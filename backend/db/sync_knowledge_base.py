"""
Pharmaco-Navigator Knowledge Base Synchronization Script
"""

import logging
import pprint
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
logger = logging.getLogger("sync_knowledge_base")

# Configuration
CPIC_BASE_URL: str = "https://api.cpicpgx.org/v1"
RXNAV_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"

# Ordered list of pharmacogenes to synchronise
TARGET_GENES: list[str] = ["CYP2D6", "CYP2C19", "SLCO1B1", "ABCB1"]

# Human-readable CPIC evidence-level labels used in source comments
GENE_LEVEL_LABELS: dict[str, str] = {
    "CYP2D6": "Level A",
    "CYP2C19": "Level A/B",
    "SLCO1B1": "Level A",
    "ABCB1": "Level B",
}

REQUEST_TIMEOUT: float = 30.0  # seconds per HTTP call

# Resolve output path relative to this script so it works from any cwd.
_SCRIPT_DIR: Path = Path(__file__).resolve().parent          # backend/db/
_BACKEND_DIR: Path = _SCRIPT_DIR.parent                      # backend/
FALLBACK_GUIDELINES_PATH: Path = (
    _BACKEND_DIR / "app" / "core" / "fallback_guidelines.py"
)

# HTTP client factory
def _make_client() -> httpx.Client:
    """Return a configured synchronous httpx client."""
    return httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={
            "Accept": "application/json",
            "User-Agent": "pharmaco-navigator-sync/1.0",
        },
    )

# CPIC API helpers
def fetch_cpic_recommendations(
    gene: str,
    client: httpx.Client,
) -> list[dict[str, Any]]:
    """
    Fetch all CPIC recommendations for *gene* and filter to Level A/B only.
    """
    url = f"{CPIC_BASE_URL}/recommendation"
    params: dict[str, str] = {"genesymbol": gene}

    logger.info("Fetching CPIC recommendations for %s …", gene)

    try:
        response = client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.error(
            "Timeout contacting CPIC API for gene %s (%.0fs limit): %s",
            gene,
            REQUEST_TIMEOUT,
            exc,
        )
        sys.exit(1)
    except httpx.RequestError as exc:
        logger.error(
            "Connection error fetching CPIC data for gene %s: %s",
            gene,
            exc,
        )
        sys.exit(1)

    if response.status_code == 429:
        logger.error(
            "CPIC API responded with 429 Too Many Requests for gene %s. "
            "Aborting sync to avoid partial data write.",
            gene,
        )
        sys.exit(1)

    if response.status_code != 200:
        logger.error(
            "CPIC API returned HTTP %d for gene %s. Response: %s",
            response.status_code,
            gene,
            response.text[:300],
        )
        sys.exit(1)

    try:
        records: Any = response.json()
    except Exception as exc: 
        logger.error("Failed to parse CPIC JSON response for gene %s: %s", gene, exc)
        sys.exit(1)

    if not isinstance(records, list):
        logger.error(
            "Unexpected CPIC response shape for gene %s — "
            "expected list, got %s.",
            gene,
            type(records).__name__,
        )
        sys.exit(1)

    # Retain only Level A and Level B evidence recommendations
    filtered: list[dict[str, Any]] = [
        rec
        for rec in records
        if isinstance(rec.get("guideline"), dict)
        and rec["guideline"].get("level", "").upper() in {"A", "B"}
    ]

    logger.info(
        "  %s: %d total records → %d Level A/B retained after filter",
        gene,
        len(records),
        len(filtered),
    )
    return filtered

# RxNav API helpers
def validate_drug_rxnav(drug_name: str, client: httpx.Client) -> bool:
    """
    Check whether *drug_name* is recognised by the NLM RxNav API.
    """
    url = f"{RXNAV_BASE_URL}/approximateTerm.json"
    params: dict[str, str] = {"term": drug_name, "maxEntries": "1"}

    try:
        response = client.get(url, params=params)
    except httpx.TimeoutException as exc:
        logger.error(
            "Timeout querying RxNav for drug '%s' (%.0fs limit): %s",
            drug_name,
            REQUEST_TIMEOUT,
            exc,
        )
        sys.exit(1)
    except httpx.RequestError as exc:
        logger.error(
            "Connection error querying RxNav for drug '%s': %s",
            drug_name,
            exc,
        )
        sys.exit(1)

    if response.status_code == 429:
        logger.error(
            "RxNav API responded with 429 Too Many Requests for drug '%s'. "
            "Aborting sync.",
            drug_name,
        )
        sys.exit(1)

    if response.status_code != 200:
        logger.warning(
            "RxNav returned HTTP %d for drug '%s'; skipping RxCUI validation.",
            response.status_code,
            drug_name,
        )
        return True  # Non-fatal — don't abort the sync for a single drug

    try:
        data: Any = response.json()
    except Exception:  # noqa: BLE001
        logger.warning(
            "Could not parse RxNav JSON for drug '%s'; skipping validation.",
            drug_name,
        )
        return True

    candidates: list = (
        data.get("approximateGroup", {}).get("candidate") or []
    )
    recognised = bool(candidates)

    if recognised:
        top_rxcui = candidates[0].get("rxcui", "unknown")
        logger.debug(
            "RxNav validated '%s' → RxCUI %s (score=%s)",
            drug_name,
            top_rxcui,
            candidates[0].get("score", "?"),
        )
    else:
        logger.warning(
            "RxNav did not return a candidate RxCUI for drug '%s'. "
            "CPIC record will still be included.",
            drug_name,
        )

    return recognised

# Data assembly
def _extract_phenotype(record: dict[str, Any], gene: str) -> str:
    """
    Extract the phenotype label for *gene* from a CPIC recommendation record.
    """
    # Primary: phenotypes dict  e.g. {"CYP2D6": "Poor Metabolizer"}
    phenotypes = record.get("phenotypes")
    if isinstance(phenotypes, dict):
        value = phenotypes.get(gene) or next(iter(phenotypes.values()), None)
        if value:
            return str(value).strip()

    # Secondary: lookupkey dict (alternative CPIC field name)
    lookupkey = record.get("lookupkey")
    if isinstance(lookupkey, dict):
        value = lookupkey.get(gene) or next(iter(lookupkey.values()), None)
        if value:
            return str(value).strip()

    # Tertiary: flat string fields
    for field in ("phenotype", "phenotypename", "EHR_PRIORITY"):
        flat = record.get(field)
        if flat and isinstance(flat, str) and flat.strip():
            return flat.strip()

    return ""


def build_gene_guidelines(
    gene: str,
    records: list[dict[str, Any]],
    client: httpx.Client,
) -> dict[str, list[dict[str, Any]]]:
    """
    Group CPIC *records* by phenotype and build the per-gene guidelines dict.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    validated_drugs: set[str] = set()

    for rec in records:
        phenotype = _extract_phenotype(rec, gene)
        if not phenotype:
            logger.debug(
                "Skipping CPIC record with no resolvable phenotype: drugname=%s",
                rec.get("drugname"),
            )
            continue

        drug_name: str = (
            rec.get("drugname")
            or (rec.get("drug") or {}).get("name")
            or "Unknown"
        )
        recommendation_text: str = (
            rec.get("recommendation") or rec.get("rxrecommendation") or ""
        )
        classification: str = (
            rec.get("classification") or rec.get("pgkbcalevel") or "Unspecified"
        )
        guideline_obj: dict = rec.get("guideline") or {}
        guideline_level: str = guideline_obj.get("level", "").upper()
        guideline_url: str = (
            guideline_obj.get("url")
            or guideline_obj.get("guidelineUrl")
            or "https://cpicpgx.org/guidelines/"
        )

        # Validate each unique drug name against RxNav once per sync run
        if drug_name not in validated_drugs:
            validate_drug_rxnav(drug_name, client)
            validated_drugs.add(drug_name)

        entry: dict[str, Any] = {
            "drugname": drug_name,
            "recommendation": recommendation_text,
            "classification": classification,
            "guideline": {
                "level": guideline_level,
                "url": guideline_url,
            },
        }

        grouped.setdefault(phenotype, []).append(entry)

    total_entries = sum(len(v) for v in grouped.values())
    logger.info(
        "  %s: built %d phenotype bucket(s) with %d total entries",
        gene,
        len(grouped),
        total_entries,
    )
    return grouped

# Source-file generation
# Verbatim helper functions preserved at the bottom of the generated file
_HELPER_FUNCTIONS: str = textwrap.dedent(
    '''\
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
    '''
)


def generate_guidelines_source(
    guidelines_by_gene: dict[str, dict[str, list[dict[str, Any]]]],
    sync_timestamp: str,
) -> str:
    """
    Produce the complete text of ``fallback_guidelines.py`` as a single string.
    """
    parts: list[str] = []

    # Module docstring
    parts.append(
        f'"""\n'
        f"Fallback CPIC Guidelines for offline operation.\n"
        f"Provides local backup of Level A/B drug-gene recommendations when "
        f"the CPIC API is unavailable.\n"
        f"\n"
        f"Auto-generated by backend/db/sync_knowledge_base.py\n"
        f"Last synchronised: {sync_timestamp}\n"
        f'"""\n'
    )

    # Imports
    parts.append("from typing import Dict, List, Any\n\n")

    # Per-gene constant blocks
    var_names: list[tuple[str, str]] = []

    for gene in TARGET_GENES:
        gene_data = guidelines_by_gene.get(gene, {})
        var_name = f"{gene}_GUIDELINES"
        var_names.append((gene, var_name))

        level_label = GENE_LEVEL_LABELS.get(gene, "Level A/B")

        # pprint.pformat produces valid Python syntax; black will reformat it
        data_repr = pprint.pformat(gene_data, indent=4, sort_dicts=False)

        parts.append(
            f"# {gene} Guidelines ({level_label})\n"
            f"{var_name}: Dict[str, List[Dict[str, Any]]] = {data_repr}\n\n\n"
        )

    # Unified registry
    registry_lines: list[str] = [
        "# Unified Fallback Registry",
        "FALLBACK_GUIDELINES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {",
    ]
    for gene, var_name in var_names:
        registry_lines.append(f'    "{gene}": {var_name},')
    registry_lines.append("}\n\n")
    parts.append("\n".join(registry_lines))

    # Helper functions
    parts.append(_HELPER_FUNCTIONS)

    return "".join(parts)

# Entry point
def main() -> None:
    """
    Orchestrate the full knowledge-base synchronisation pipeline.
    """
    logger.info("=" * 60)
    logger.info("Pharmaco-Navigator Knowledge Base Sync")
    logger.info("Target genes : %s", TARGET_GENES)
    logger.info("Output file  : %s", FALLBACK_GUIDELINES_PATH)
    logger.info("=" * 60)

    sync_timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    guidelines_by_gene: dict[str, dict[str, list[dict[str, Any]]]] = {}

    with _make_client() as client:
        for gene in TARGET_GENES:
            logger.info("--- Processing gene: %s ---", gene)
            cpic_records = fetch_cpic_recommendations(gene, client)
            guidelines_by_gene[gene] = build_gene_guidelines(
                gene, cpic_records, client
            )

    # Summarize what was collected
    for gene, buckets in guidelines_by_gene.items():
        total = sum(len(v) for v in buckets.values())
        logger.info(
            "  %-10s  %2d phenotype bucket(s)  %3d recommendation entries",
            gene,
            len(buckets),
            total,
        )

    # Generate Python source
    source = generate_guidelines_source(guidelines_by_gene, sync_timestamp)

    # Atomic write: write to a .tmp sibling then rename so a partial failure never corrupts the live file.
    tmp_path = FALLBACK_GUIDELINES_PATH.with_suffix(".py.tmp")
    try:
        tmp_path.write_text(source, encoding="utf-8")
        tmp_path.replace(FALLBACK_GUIDELINES_PATH)
    except OSError as exc:
        logger.error(
            "Failed to write updated guidelines to %s: %s",
            FALLBACK_GUIDELINES_PATH,
            exc,
        )
        sys.exit(1)
    finally:
        # Clean up temp file if replace failed
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    file_size = FALLBACK_GUIDELINES_PATH.stat().st_size
    logger.info(
        "Successfully wrote %s (%d bytes, %d lines)",
        FALLBACK_GUIDELINES_PATH,
        file_size,
        source.count("\n"),
    )
    logger.info("=" * 60)
    logger.info("Sync complete — run 'black backend/app/core/fallback_guidelines.py' to format.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
