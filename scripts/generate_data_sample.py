"""Generate the synthetic datasets under data_sample/.

This repository distributes the analysis, not the data: no real dataset is
committed, and data_sample/ is a fully synthetic stand-in with the same
schema as the processed outputs of the collection pipeline, so the notebook
runs end-to-end on a fresh clone.

Geography is real: province names, abbreviations and regions are public
facts, read from geo/provinces.geojson. Every count and every entity
is auto-generated. The sport dimension mirrors the pipeline's published
granularity: area-level values (16 federation-inspired areas), never
fine-grained sport labels. Generation is deterministic (fixed seed):
re-running the script reproduces the committed sample exactly.

The sample also reproduces two quirks of the collected data, so the
harmonization step documented in the notebook exercises real logic instead
of a no-op:
- a few Sardinian entities carry province codes abolished by the 2016
  reform (CI, OG, OT): the export keeps the code each entity was
  registered under;
- Valle d'Aosta entities carry the non-standard region code "VAO".

Outputs:
- data_sample/registry_entity_counts_by_province.csv
- data_sample/platform_entity_counts_by_province.csv
- data_sample/platform_entities.json
"""

import csv
import json
import logging
import random
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
GEO_PROVINCES: Path = PROJECT_ROOT / "geo" / "provinces.geojson"
SAMPLE_DIR: Path = PROJECT_ROOT / "data_sample"

# Any fixed value works: this one date-stamps when the sample was designed.
SEED: int = 20260824

# Fixed synthetic envelope values: the notebook only reads "items", but the
# sample mirrors the full schema of the real sanitized export (retrieved_at
# uses the same YYYYMMDD_HHMMSS shape, with an obviously fake value).
RETRIEVED_AT: str = "20260101_000000"
DIMENSION: str = "platform_entities"

N_ENTITIES: int = 2000

# Standard region abbreviations (public facts), keyed by the region names
# used in the boundary file. Valle d'Aosta is emitted as "VAO" at generation
# time to mirror the quirk in the collected data the notebook harmonizes.
REGION_NAME_TO_CODE: dict[str, str] = {
    "Abruzzo": "ABR",
    "Basilicata": "BAS",
    "Calabria": "CAL",
    "Campania": "CAM",
    "Emilia-Romagna": "EMR",
    "Friuli-Venezia Giulia": "FVG",
    "Lazio": "LAZ",
    "Liguria": "LIG",
    "Lombardia": "LOM",
    "Marche": "MAR",
    "Molise": "MOL",
    "Piemonte": "PIE",
    "Puglia": "PUG",
    "Sardegna": "SAR",
    "Sicilia": "SIC",
    "Toscana": "TOS",
    "Trentino-Alto Adige/Südtirol": "TAA",
    "Umbria": "UMB",
    "Valle d'Aosta/Vallée d'Aoste": "VDA",
    "Veneto": "VEN",
}

# Same map the collection pipeline applies at aggregation time: codes
# abolished by the 2016 Sardinian reform merge into their successors.
PROVINCE_ABBR_HARMONIZATION: dict[str, str] = {"CI": "SU", "OG": "NU", "OT": "SS"}

# Entities frozen under pre-2016 codes, appended on top of N_ENTITIES with
# registration years compatible with an abolished code (echoing the real
# proportions: CI > OT > OG). Guarantees the harmonization path is visibly
# exercised on the sample, which random draws alone would not.
LEGACY_SARDINIAN_ENTITIES: dict[str, int] = {"CI": 8, "OG": 3, "OT": 5}
LEGACY_YEARS: tuple[int, ...] = (2015, 2016)

# The published sport taxonomy: 16 federation-inspired areas, exactly as the
# collection pipeline emits them (fine-grained sport labels never leave the
# pipeline). Weights are hand-picked but echo a plausible Italian market shape:
# a football-heavy head, a gym/dance-heavy second, a long tail.
AREA_WEIGHTS: dict[str, int] = {
    "Football": 20,
    "Gymnastics & Dance": 18,
    "Fitness & Wellness": 10,
    "Martial Arts & Combat": 9,
    "Volleyball": 9,
    "Basketball": 7,
    "Athletics & Endurance": 4,
    "Tennis & Racquet Sports": 4,
    "Water & Nautical Sports": 3,
    "Winter & Mountain Sports": 3,
    "Cycling & Motors": 2,
    "Skating & Rollersports": 2,
    "Team Sports (Other)": 2,
    "Precision & Target Sports": 1,
    "Equestrian & Dog Sports": 1,
    "Other Activities": 1,
}


def pick_areas(rng: random.Random, k: int) -> list[str]:
    """Draw k distinct areas, respecting the hand-picked popularity weights.

    random.sample(counts=...) samples a multiset and could return the same
    area twice, so the draw removes each picked area from the pool instead:
    entities never list an area more than once, like the real export.

    :param rng: seeded generator, sole source of randomness
    :param k: number of areas to draw
    :return: sorted distinct areas
    """
    pool: list[str] = list(AREA_WEIGHTS)
    weights: list[int] = list(AREA_WEIGHTS.values())
    chosen: list[str] = []
    for _ in range(k):
        pick: str = rng.choices(pool, weights=weights, k=1)[0]
        index: int = pool.index(pick)
        pool.pop(index)
        weights.pop(index)
        chosen.append(pick)
    return sorted(chosen)

# Registration years with quadratically growing weights: the sample shows
# the same "young, accelerating platform" shape as the real trend analysis.
YEARS: tuple[int, ...] = tuple(range(2015, 2026))
YEAR_WEIGHTS: tuple[int, ...] = tuple((i + 1) ** 2 for i in range(len(YEARS)))


def load_provinces() -> list[dict[str, Any]]:
    """Return the properties of the 107 real provinces from the boundary file.

    :return: one dict per province (prov_name, prov_acr, reg_name, ISTAT codes)
    """
    with GEO_PROVINCES.open(encoding="utf-8") as f:
        geo: dict[str, Any] = json.load(f)
    return [feature["properties"] for feature in geo["features"]]


def build_entities(
    rng: random.Random, provinces: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Auto-generate the entity-level platform sample (sanitized-export schema).

    :param rng: seeded generator, sole source of randomness
    :param provinces: real province properties from the boundary file
    :return: items shaped like the sanitized export (sport, registration_year,
        province_abbr, region_code)
    """
    # Skewed province weights: a few large markets, a long tail. Some
    # provinces may legitimately end up with zero entities: the notebook's
    # left-merge covers them, and the choropleth shows them as "No data".
    weights: list[float] = [rng.lognormvariate(0.0, 1.0) for _ in provinces]

    items: list[dict[str, Any]] = []
    for prov in rng.choices(provinces, weights=weights, k=N_ENTITIES):
        region_code: str = REGION_NAME_TO_CODE[prov["reg_name"]]
        if region_code == "VDA":
            region_code = "VAO"  # quirk of the collected data, harmonized downstream

        n_areas: int = rng.choices((1, 2, 3), weights=(70, 22, 8))[0]
        items.append(
            {
                "sport": pick_areas(rng, n_areas),
                "registration_year": rng.choices(YEARS, weights=YEAR_WEIGHTS)[0],
                "province_abbr": prov["prov_acr"],
                "region_code": region_code,
            }
        )

    for legacy_code, count in LEGACY_SARDINIAN_ENTITIES.items():
        for _ in range(count):
            items.append(
                {
                    "sport": pick_areas(
                        rng, rng.choices((1, 2), weights=(80, 20))[0]
                    ),
                    "registration_year": rng.choice(LEGACY_YEARS),
                    "province_abbr": legacy_code,
                    "region_code": "SAR",
                }
            )

    # The real export has no meaningful order; shuffling avoids the legacy
    # block sitting recognizably at the tail of the file.
    rng.shuffle(items)
    return items


def aggregate_platform(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate entities per province, mirroring the pipeline's aggregation step.

    Applies the same harmonization the pipeline applies, so the sample counts
    CSV, like the real one, contains only current province codes.

    :param items: entity-level sample
    :return: one row per province, sorted by province_abbr
    """
    code_to_name: dict[str, str] = {
        code: name for name, code in REGION_NAME_TO_CODE.items()
    }
    code_to_name["VAO"] = code_to_name["VDA"]

    counts: dict[str, int] = {}
    region_of: dict[str, str] = {}
    for item in items:
        abbr: str = PROVINCE_ABBR_HARMONIZATION.get(
            item["province_abbr"], item["province_abbr"]
        )
        counts[abbr] = counts.get(abbr, 0) + 1
        region_of.setdefault(abbr, item["region_code"])

    return [
        {
            "region_code": region_of[abbr],
            "region_name": code_to_name.get(region_of[abbr], region_of[abbr]),
            "province_abbr": abbr,
            "platform_entities": counts[abbr],
        }
        for abbr in sorted(counts)
    ]


def build_registry(
    rng: random.Random,
    provinces: list[dict[str, Any]],
    platform_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Auto-generate registry totals for all 107 provinces (registry-CSV schema).

    Ids are the ISTAT numeric codes carried by the boundary file; the real
    registry uses its own id scheme, but the analysis never joins on ids
    (province_abbr is the only cross-source key), so any plausible integer id
    keeps the schema honest.

    :param rng: seeded generator, sole source of randomness
    :param provinces: real province properties from the boundary file
    :param platform_rows: aggregated platform sample (plausibility bound)
    :return: one row per province, sorted by region then province name
    """
    platform_of: dict[str, int] = {
        row["province_abbr"]: row["platform_entities"] for row in platform_rows
    }

    rows: list[dict[str, Any]] = []
    for prov in sorted(provinces, key=lambda p: (p["reg_name"], p["prov_name"])):
        abbr: str = prov["prov_acr"]
        # Plausibility constraint: the registry is a superset of the
        # platform, so each auto-generated total must dominate the platform count.
        base: int = int(rng.lognormvariate(5.8, 0.7))
        total: int = max(base, platform_of.get(abbr, 0) * rng.randint(4, 15))
        rows.append(
            {
                "region_id": prov["reg_istat_code_num"],
                "region_name": prov["reg_name"],
                "province_id": prov["prov_istat_code_num"],
                "province_name": prov["prov_name"],
                "province_abbr": abbr,
                "entities_total": total,
            }
        )
    return rows


def write_csv(
    rows: list[dict[str, Any]], fieldnames: list[str], output_path: Path
) -> None:
    """Write rows to a UTF-8 CSV, creating parent directories if needed.

    :param rows: dictionaries to write, one per CSV row
    :param fieldnames: column names, in the exact output order
    :param output_path: destination CSV file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        # LF endings on every platform: the CI determinism step compares
        # bytes via git diff, and the csv default (CRLF) would clash with
        # git end-of-line normalization at the first checkout.
        writer: csv.DictWriter[str] = csv.DictWriter(
            f, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Build the three sample files under data_sample/."""
    rng: random.Random = random.Random(SEED)
    provinces: list[dict[str, Any]] = load_provinces()
    logger.info("Provinces loaded from boundary file: %d", len(provinces))

    items: list[dict[str, Any]] = build_entities(rng, provinces)
    platform_rows: list[dict[str, Any]] = aggregate_platform(items)
    registry_rows: list[dict[str, Any]] = build_registry(rng, provinces, platform_rows)

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    # Envelope mirrors the real processed export, including the published
    # area taxonomy (sorted, like the pipeline emits it).
    entities_payload: dict[str, Any] = {
        "dimension": DIMENSION,
        "retrieved_at": RETRIEVED_AT,
        "count": len(items),
        "sport_areas": sorted(AREA_WEIGHTS),
        "items": items,
    }
    entities_path: Path = SAMPLE_DIR / "platform_entities.json"
    with entities_path.open("w", encoding="utf-8") as f:
        json.dump(entities_payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    write_csv(
        platform_rows,
        ["region_code", "region_name", "province_abbr", "platform_entities"],
        SAMPLE_DIR / "platform_entity_counts_by_province.csv",
    )
    write_csv(
        registry_rows,
        [
            "region_id",
            "region_name",
            "province_id",
            "province_name",
            "province_abbr",
            "entities_total",
        ],
        SAMPLE_DIR / "registry_entity_counts_by_province.csv",
    )

    logger.info("Synthetic entities: %d (legacy Sardinian codes included)", len(items))
    logger.info("Platform provinces with entities: %d", len(platform_rows))
    logger.info("Registry provinces: %d", len(registry_rows))
    logger.info("Sample written to %s", SAMPLE_DIR)


if __name__ == "__main__":
    main()
