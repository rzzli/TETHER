"""Retain bounded primary-source observation metadata, not article bodies."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


sources = [
    {
        "id": "malemud2009", "publication_year": 2009, "pmid": "27789987",
        "pmcid": "PMC5074717", "doi": "10.2147/OARRR.S6266", "type": "secondary_review",
        "title": "Recent advances in neutralizing the IL-6 pathway in arthritis",
        "official_urls": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC5074717/",
                          "https://pubmed.ncbi.nlm.nih.gov/27789987/",
                          "https://www.tandfonline.com/doi/full/10.2147/oarrr.s6266"],
        "checked_locator": "Official PMC indexed introduction and conclusion; PubMed indexed identity/date.",
        "observation": "Introduction identifies sIL-6R as inhibitor; conclusion instead distinguishes sIL-6R agonism from recombinant sgp130 inhibition. Their inconsistency is visible without assuming an editorial cause.",
        "access": "Official search-index content readable. Direct PMC browser check, publisher403, EuropePMC inaccessible; direct PubMed fetch yielded HHS footer.",
        "source_bytes_pinned": False,
    },
    {
        "id": "hashizume2008", "publication_year": 2008, "pmid": "18786965",
        "doi": "10.1093/rheumatology/ken363", "type": "primary_experiment_abstract_checked",
        "title": "IL-6 trans-signalling directly induces RANKL on fibroblast-like synovial cells and is involved in RANKL induction by TNF-alpha and IL-17",
        "official_urls": ["https://pubmed.ncbi.nlm.nih.gov/18786965/"],
        "checked_locator": "PubMed Abstract Methods/Results/Conclusions",
        "observation": "RA-derived FLS stimulation and RANKL assays support the supplied IL-6/sIL-6R versus IL-6-alone contrast. Abstract reports24-hour stimulation; that new external detail cannot fill the original excerpt's missing fields.",
        "access": "Primary abstract readable directly and in official index.",
        "source_bytes_pinned": False,
    },
    {
        "id": "rochas2009", "publication_year": 2009, "pmid": "19404965",
        "doi": "10.1002/art.24498", "type": "primary_experiment_abstract_checked",
        "title": "Transmembrane BAFF from rheumatoid synoviocytes requires interleukin-6 to induce the expression of recombination-activating gene in B lymphocytes",
        "official_urls": ["https://pubmed.ncbi.nlm.nih.gov/19404965/",
                          "https://onlinelibrary.wiley.com/doi/10.1002/art.24498"],
        "checked_locator": "PubMed Abstract Methods/Results/Conclusion",
        "observation": "Healthy-control B cells were cocultured with RA/OA FLS; RAG RNA/protein and functional assays plus BAFF and IL-6-receptor perturbations support laboratory-context reporting. Donor identity is external information absent from supplied P5.",
        "access": "PubMed primary abstract readable. Publisher direct fetch403; indexed abstract also readable.",
        "source_bytes_pinned": False,
    },
    {
        "id": "jostock2001", "publication_year": 2001, "pmid": "11121117",
        "doi": "10.1046/j.1432-1327.2001.01867.x", "type": "primary_experiment_text_checked",
        "title": "Soluble gp130 is the natural inhibitor of soluble interleukin-6 receptor transsignaling responses",
        "official_urls": ["https://febs.onlinelibrary.wiley.com/doi/10.1046/j.1432-1327.2001.01867.x",
                          "https://pubmed.ncbi.nlm.nih.gov/11121117/"],
        "checked_locator": "Publisher Abstract and Results: engineered BAF/3 response experiments/Figure4",
        "observation": "Recombinant sgp130 inhibited soluble-receptor-dependent responses in the checked engineered-cell comparison, while the membrane-receptor response was spared. This resolves the molecular distinction, without proving a patient treatment benefit.",
        "access": "Publisher full text readable through web tool; official PubMed index abstract readable, direct PubMed fetch HHS footer.",
        "source_bytes_pinned": False,
    },
]
edges = [
    {"from": "malemud2009", "to": "hashizume2008", "type": "cites",
     "anchor": "SuppliedP4 author/reference43; primary identity and reported contrast match.",
     "full_seed_reference_list_refetched": False},
    {"from": "malemud2009", "to": "rochas2009", "type": "cites",
     "anchor": "SuppliedP5 reference58, task's Rochas anchor; primary identity and co-culture finding match.",
     "full_seed_reference_list_refetched": False},
    {"from": "jostock2001", "to": "malemud2009", "type": "supports_credibility_check_not_citation",
     "anchor": "Targeted foundational context; no direct seed-to-Jostock citation edge established."},
]
checks = [
    {"id": "four_canonical_sources", "pass": len({row["id"] for row in sources}) == 4},
    {"id": "three_primary_reports", "pass": sum(row["type"].startswith("primary_experiment") for row in sources) == 3},
    {"id": "all_official_sources", "pass": all(row["official_urls"] for row in sources)},
    {"id": "no_false_direct_jostock_citation", "pass": not any(row["type"] == "cites" and row["to"] == "jostock2001" for row in edges)},
    {"id": "current_not_historical_pins", "pass": all(row["source_bytes_pinned"] is False for row in sources)},
]
assert all(row["pass"] for row in checks)
record = {
    "schema_version": 1, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "SUPPORTED_SOURCE_CREDIBILITY_CONCERN_AI_DEVELOPMENT_ONLY",
    "role": "evaluation_only", "audience": "coordinator; separate from blank source-only reviewer packets",
    "skill": "citation-snowballing", "scope": "One seed, two anchored backward references, one targeted foundational primary experiment; no forward or systematic survey.",
    "packet_input": pin(ROOT / "docs/expert-review-20261026/Expert-review.html"),
    "sources": sources, "edges": edges, "checks": checks,
    "interpretation": "P3 is source-faithful but scientifically questionable. Primary evidence supports sIL-6R-dependent agonism and sgp130-mediated inhibition; source inconsistency is supported, its editorial cause and any formal erratum are not established.",
    "separation": ["source fidelity", "citation entailment", "scientific credibility", "hypothesis applicability", "clinical treatment effect"],
    "limits": ["Current web observations are not frozen historical releases.",
               "No original card, returned answer or model response was repaired.",
               "External primary-method context is not retrospectively supplied to original cards or ratings.",
               "No experiment replication or complete primary-study risk-of-bias appraisal.",
               "No independent human gate, consensus score, scientific H5 acceptance or clinical inference."],
    "scientific_validation": "not_established", "human_gate_satisfied": False,
    "provider_model_calls": 0, "article_or_dataset_files_downloaded": 0,
    "protected_outcome_files_read": 0,
    "narrative": pin(BASE / "IL6R-SOURCE-CREDIBILITY-CHECK-v1.md"),
}
output = BASE / "IL6R-SOURCE-CREDIBILITY-CHECK-v1.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, indent=2, ensure_ascii=True)
    stream.write("\n")
print(json.dumps({"report": pin(output), "narrative": record["narrative"], "checks": len(checks), "all_pass": True}))
