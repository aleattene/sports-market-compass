"""Data contract tests for the synthetic sample.

The README promises that a fresh clone runs end-to-end on data_sample/
alone. The notebook relies on a precise contract to keep that promise:
file schemas, the 107-province universe, only current province codes in
the aggregated counts, and internal consistency between the three files.
These tests pin that contract, so a drifting generator or a malformed
sample fails fast here instead of deep inside the notebook.

Run with: pytest
"""

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

SAMPLE_DIR: Path = Path(__file__).resolve().parents[1] / "data_sample"

# Same one-way map documented in the README: codes abolished by the 2016
# Sardinian reform merge into their successors. Aggregated counts must
# contain only the right-hand side; the entity-level export may carry the
# left-hand side, so the notebook's harmonization runs on real logic.
HARMONIZATION: dict[str, str] = {"CI": "SU", "OG": "NU", "OT": "SS"}


@pytest.fixture(scope="module")
def registry() -> pd.DataFrame:
    # keep_default_na=False is part of the contract: Napoli's abbreviation
    # is literally "NA" and must survive the read as a string, not NaN.
    return pd.read_csv(
        SAMPLE_DIR / "registry_entity_counts_by_province.csv",
        keep_default_na=False,
    )


@pytest.fixture(scope="module")
def platform() -> pd.DataFrame:
    return pd.read_csv(
        SAMPLE_DIR / "platform_entity_counts_by_province.csv",
        keep_default_na=False,
    )


@pytest.fixture(scope="module")
def entities() -> dict[str, Any]:
    with (SAMPLE_DIR / "platform_entities.json").open(encoding="utf-8") as f:
        return json.load(f)


class TestRegistryCounts:
    def test_schema(self, registry: pd.DataFrame) -> None:
        assert list(registry.columns) == [
            "region_id",
            "region_name",
            "province_id",
            "province_name",
            "province_abbr",
            "entities_total",
        ]

    def test_covers_all_107_provinces(self, registry: pd.DataFrame) -> None:
        # The registry is the market universe: every current Italian
        # province appears exactly once, none is duplicated or missing.
        assert len(registry) == 107
        assert registry["province_abbr"].is_unique

    def test_napoli_survives_the_read(self, registry: pd.DataFrame) -> None:
        # The canonical read keeps "NA" as a string; with pandas defaults
        # Napoli would become NaN and silently vanish from merges.
        assert "NA" in set(registry["province_abbr"])

    def test_only_current_province_codes(self, registry: pd.DataFrame) -> None:
        abbrs = set(registry["province_abbr"])
        # Abolished Sardinian codes never appear at registry level, and VS
        # does not exist in the layout at the snapshot date (see README).
        assert abbrs.isdisjoint(HARMONIZATION)
        assert "VS" not in abbrs
        # Their successors do appear.
        assert set(HARMONIZATION.values()) <= abbrs

    def test_totals_are_positive_integers(self, registry: pd.DataFrame) -> None:
        assert pd.api.types.is_integer_dtype(registry["entities_total"])
        assert (registry["entities_total"] > 0).all()


class TestPlatformCounts:
    def test_schema(self, platform: pd.DataFrame) -> None:
        assert list(platform.columns) == [
            "region_code",
            "region_name",
            "province_abbr",
            "platform_entities",
        ]

    def test_provinces_are_a_subset_of_the_registry(
        self, platform: pd.DataFrame, registry: pd.DataFrame
    ) -> None:
        # province_abbr is the only cross-source join key: every platform
        # province must resolve against the registry universe.
        assert platform["province_abbr"].is_unique
        assert set(platform["province_abbr"]) <= set(registry["province_abbr"])

    def test_counts_are_positive_integers(self, platform: pd.DataFrame) -> None:
        # Zero-entity provinces are simply absent from the file: the
        # notebook's left merge reintroduces them on the registry side.
        assert pd.api.types.is_integer_dtype(platform["platform_entities"])
        assert (platform["platform_entities"] > 0).all()

    def test_at_least_one_province_has_no_entities(
        self, platform: pd.DataFrame, registry: pd.DataFrame
    ) -> None:
        # The sample deliberately leaves at least one province uncovered,
        # so the "No data" path (choropleth hatching, zero-coverage rows)
        # is exercised on a fresh clone and not only on real data.
        assert set(platform["province_abbr"]) < set(registry["province_abbr"])

    def test_only_current_province_codes(self, platform: pd.DataFrame) -> None:
        # Aggregation happens after harmonization: abolished codes must
        # never reach the counts, whatever the entity-level export carries.
        assert set(platform["province_abbr"]).isdisjoint(HARMONIZATION)

    def test_registry_dominates_platform(
        self, platform: pd.DataFrame, registry: pd.DataFrame
    ) -> None:
        # The platform serves a subset of the registered market, so the
        # coverage gap the notebook computes must never go negative.
        totals = registry.set_index("province_abbr")["entities_total"]
        for row in platform.itertuples():
            assert totals[row.province_abbr] >= row.platform_entities


class TestEntitiesExport:
    def test_envelope_schema(self, entities: dict[str, Any]) -> None:
        assert set(entities) == {
            "dimension",
            "retrieved_at",
            "count",
            "sport_areas",
            "items",
        }
        assert entities["dimension"] == "platform_entities"
        # Same YYYYMMDD_HHMMSS shape as the real export envelope.
        assert re.fullmatch(r"\d{8}_\d{6}", entities["retrieved_at"])

    def test_count_matches_items(self, entities: dict[str, Any]) -> None:
        assert entities["count"] == len(entities["items"])

    def test_sport_area_taxonomy(self, entities: dict[str, Any]) -> None:
        areas = entities["sport_areas"]
        # The published taxonomy: 16 areas, declared by the payload itself,
        # sorted and free of duplicates.
        assert len(areas) == 16
        assert len(set(areas)) == 16
        assert areas == sorted(areas)

    def test_items_shape(self, entities: dict[str, Any]) -> None:
        areas = set(entities["sport_areas"])
        for item in entities["items"]:
            assert set(item) == {
                "sport",
                "registration_year",
                "province_abbr",
                "region_code",
            }
            # Area-level values only, each listed at most once per entity.
            assert 1 <= len(item["sport"]) <= 3
            assert len(set(item["sport"])) == len(item["sport"])
            assert set(item["sport"]) <= areas
            # A missing year is legal (real collections have them); when
            # present it must be a plausible calendar year.
            year = item["registration_year"]
            assert year is None or (isinstance(year, int) and 2000 <= year <= 2026)

    def test_legacy_sardinian_codes_are_exercised(
        self, entities: dict[str, Any]
    ) -> None:
        # The entity-level export must carry at least one abolished code,
        # otherwise the notebook's harmonization step degrades to a no-op
        # and stops being tested by a fresh clone.
        abbrs = {item["province_abbr"] for item in entities["items"]}
        assert set(HARMONIZATION) <= abbrs

    def test_vao_region_quirk_is_preserved(self, entities: dict[str, Any]) -> None:
        # The export carries "VAO" for Valle d'Aosta, so the notebook's
        # region alias handling runs on real input.
        region_codes = {item["region_code"] for item in entities["items"]}
        assert "VAO" in region_codes
        assert "VDA" not in region_codes

    def test_counts_are_the_aggregation_of_the_entities(
        self, entities: dict[str, Any], platform: pd.DataFrame
    ) -> None:
        # The two platform files describe the same population: aggregating
        # the entity-level export by harmonized province must reproduce the
        # counts CSV exactly, row for row.
        expected: dict[str, int] = {}
        for item in entities["items"]:
            abbr = HARMONIZATION.get(item["province_abbr"], item["province_abbr"])
            expected[abbr] = expected.get(abbr, 0) + 1
        actual = dict(
            zip(platform["province_abbr"], platform["platform_entities"])
        )
        assert actual == expected
