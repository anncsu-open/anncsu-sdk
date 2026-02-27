"""Tests for OAS response field mapping fixes (Issue #12).

The OAS specs define `denomuff` but the real API returns `duf`.
Additionally, `cododocomunale` and `codacccomunale` are returned
by the API but missing from OAS specs.

These tests verify that the Pydantic models correctly map the real
API field names to the expected Python field names via aliases.
"""

from pathlib import Path

import pytest

from anncsu.pa.models import (
    ElencoOdonimiGetPathParamData,
    ElencoOdonimiGetQueryParamData,
    ElencoOdonimiPostData,
    ElencoodonimiprogGetPathParamData,
    ElencoodonimiprogGetQueryParamData,
    ElencoodonimiprogPostData,
    PrognazaccGetPathParamData,
    PrognazaccGetQueryParamData,
    PrognazaccPostData,
    PrognazareaGetPathParamData,
    PrognazareaGetQueryParamData,
    PrognazareaPostData,
)


class TestDenomuffAlias:
    """Test that the `denomuff` field accepts the `duf` alias from the real API."""

    def test_denomuff_alias_maps_duf(self):
        """Construct model from JSON with `duf` -> `item.denomuff` returns value."""
        item = PrognazaccGetQueryParamData.model_validate({"duf": "ANDREOTTO SARACINI"})
        assert item.denomuff == "ANDREOTTO SARACINI"

    def test_denomuff_python_name_still_works(self):
        """Construct model with `denomuff` kwarg -> still works (populate_by_name)."""
        item = PrognazaccGetQueryParamData(denomuff="VIA ROMA")
        assert item.denomuff == "VIA ROMA"

    def test_model_dump_by_alias_uses_duf(self):
        """`model_dump(by_alias=True)` outputs `duf` not `denomuff`."""
        item = PrognazaccGetQueryParamData.model_validate({"duf": "ANDREOTTO SARACINI"})
        dumped = item.model_dump(by_alias=True, exclude_none=True)
        assert "duf" in dumped
        assert "denomuff" not in dumped
        assert dumped["duf"] == "ANDREOTTO SARACINI"


class TestMissingFields:
    """Test that extra fields from the real API are captured."""

    def test_cododocomunale_field_exists(self):
        """Construct model from JSON with `cododocomunale` -> field accessible."""
        item = PrognazaccGetQueryParamData.model_validate({"cododocomunale": "5786"})
        assert item.cododocomunale == "5786"

    def test_codacccomunale_field_exists(self):
        """Construct prognazacc model with `codacccomunale` -> field accessible."""
        item = PrognazaccGetQueryParamData.model_validate({"codacccomunale": "1234"})
        assert item.codacccomunale == "1234"


class TestFullResponseParsing:
    """Test parsing a complete real API response."""

    def test_full_prognazacc_response_parsing(self):
        """Parse the exact real API JSON response -> all fields populated."""
        raw = {
            "prognaz": "907000",
            "cododocomunale": "5786",
            "dug": "VIA",
            "duf": "ANDREOTTO SARACINI",
            "denomloc": "",
            "denomlingua1": "",
            "denomlingua2": "",
            "prognazacc": "5865223",
            "codacccomunale": "",
            "civico": "43",
            "esp": "",
            "specif": "",
            "metrico": "",
            "coordX": "12,2770279",
            "coordY": "41,7329632",
            "quota": "0",
            "metodo": "3",
        }
        item = PrognazaccGetQueryParamData.model_validate(raw)

        assert item.prognaz == "907000"
        assert item.cododocomunale == "5786"
        assert item.dug == "VIA"
        assert item.denomuff == "ANDREOTTO SARACINI"
        assert item.denomloc == ""
        assert item.prognazacc == "5865223"
        assert item.codacccomunale == ""
        assert item.civico == "43"
        assert item.coord_x == "12,2770279"
        assert item.coord_y == "41,7329632"
        assert item.quota == "0"
        assert item.metodo == "3"


ALL_DATA_MODELS = [
    ElencoOdonimiGetPathParamData,
    ElencoOdonimiGetQueryParamData,
    ElencoOdonimiPostData,
    ElencoodonimiprogGetPathParamData,
    ElencoodonimiprogGetQueryParamData,
    ElencoodonimiprogPostData,
    PrognazareaGetPathParamData,
    PrognazareaGetQueryParamData,
    PrognazareaPostData,
    PrognazaccGetPathParamData,
    PrognazaccGetQueryParamData,
    PrognazaccPostData,
]


class TestAllModelsHaveAlias:
    """Parametrized test: all 12 Data classes have `duf` alias on `denomuff`."""

    @pytest.mark.parametrize("model_cls", ALL_DATA_MODELS, ids=lambda c: c.__name__)
    def test_all_affected_models_have_duf_alias(self, model_cls):
        """Each model class should accept `duf` and map it to `denomuff`."""
        item = model_cls.model_validate({"duf": "TEST STREET"})
        assert item.denomuff == "TEST STREET"

    @pytest.mark.parametrize("model_cls", ALL_DATA_MODELS, ids=lambda c: c.__name__)
    def test_all_affected_models_have_cododocomunale(self, model_cls):
        """Each model class should have the `cododocomunale` field."""
        item = model_cls.model_validate({"cododocomunale": "1234"})
        assert item.cododocomunale == "1234"


# --- Sentinel tests ---
# These tests detect when Agenzia delle Entrate corrects the OAS specs,
# so we know to remove the workaround (aliases + extra fields).

OAS_SPEC = (
    Path(__file__).parent.parent.parent
    / "oas"
    / "dev"
    / "Specifica API - ANNCSU \u2013 Consultazione per le PA.yaml"
)


class TestOASWorkaroundSentinel:
    """Sentinel: detect when OAS specs are corrected so we can remove the workaround.

    These tests PASS as long as the OAS specs still contain the wrong field name
    `denomuff`. When Agenzia delle Entrate corrects the specs to use `duf`, these
    tests will FAIL with a clear message telling us to remove the workaround.

    See: https://github.com/geobeyond/anncsu-sdk/issues/12
    """

    def test_oas_still_uses_denomuff(self):
        """Sentinel: OAS spec should still contain `denomuff` (the wrong name).

        If this test FAILS, it means the OAS spec has been corrected to use `duf`.
        ACTION REQUIRED: Remove the `alias="duf"` workaround from all 12 model
        files and from `post_speakeasy_generation.py`. See Issue #12.
        """
        content = OAS_SPEC.read_text()
        assert "denomuff" in content, (
            "OAS spec no longer contains 'denomuff'! "
            "Agenzia delle Entrate has likely corrected the spec to use 'duf'. "
            "ACTION REQUIRED: Remove the alias workaround from model files and "
            "post_speakeasy_generation.py. See Issue #12."
        )

    def test_oas_does_not_yet_contain_duf(self):
        """Sentinel: OAS spec should NOT yet contain `duf` as a field name.

        If this test FAILS, it means the OAS spec now uses `duf` and Speakeasy
        will generate the correct field name natively.
        ACTION REQUIRED: Remove the `alias="duf"` workaround. See Issue #12.
        """
        content = OAS_SPEC.read_text()
        # Match `duf:` as a YAML key (indented, followed by colon)
        # but not as part of `denomuff:`
        import re

        duf_as_field = re.findall(r"^\s+duf:\s*$", content, re.MULTILINE)
        assert len(duf_as_field) == 0, (
            f"OAS spec now contains 'duf' as a field name ({len(duf_as_field)} "
            "occurrences)! Agenzia delle Entrate has corrected the spec. "
            "ACTION REQUIRED: Remove the alias workaround from model files and "
            "post_speakeasy_generation.py. See Issue #12."
        )

    def test_oas_does_not_yet_contain_cododocomunale(self):
        """Sentinel: OAS spec should NOT yet contain `cododocomunale`.

        If this test FAILS, it means the OAS spec now includes this field
        and Speakeasy will generate it natively.
        ACTION REQUIRED: Remove the manual `cododocomunale` field addition
        from model files and post_speakeasy_generation.py. See Issue #12.
        """
        content = OAS_SPEC.read_text()
        assert "cododocomunale" not in content, (
            "OAS spec now contains 'cododocomunale'! "
            "ACTION REQUIRED: Remove the manual field addition from model files "
            "and post_speakeasy_generation.py. See Issue #12."
        )

    def test_oas_does_not_yet_contain_codacccomunale(self):
        """Sentinel: OAS spec should NOT yet contain `codacccomunale`.

        If this test FAILS, it means the OAS spec now includes this field
        and Speakeasy will generate it natively.
        ACTION REQUIRED: Remove the manual `codacccomunale` field addition
        from prognazacc model files and post_speakeasy_generation.py. See Issue #12.
        """
        content = OAS_SPEC.read_text()
        assert "codacccomunale" not in content, (
            "OAS spec now contains 'codacccomunale'! "
            "ACTION REQUIRED: Remove the manual field addition from prognazacc "
            "model files and post_speakeasy_generation.py. See Issue #12."
        )
