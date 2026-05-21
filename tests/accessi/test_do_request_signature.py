"""Regression tests for issue #26.

Speakeasy 1.7+ generates `BaseSDK.do_request(... is_error_status_code=lambda
c: utils.match_status_codes(LIST, c), ...)` but the actual base-class
signature accepts `error_status_codes` (a list) — not a predicate. The
generated kwarg name is therefore wrong and every real API call explodes
with ``TypeError: do_request() got an unexpected keyword argument
'is_error_status_code'``.

The pre-existing CLI Accessi tests mock the SDK layer entirely, so this
bug only surfaces during a real end-to-end call. These tests close the
gap by patching ``BaseSDK.do_request`` with a function whose signature
mirrors the real one — any extra kwarg raises ``TypeError`` immediately,
which is exactly the RED condition we want before the fix.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import httpx
import pytest

from anncsu.accessi import AnncsuAccessi
from anncsu.accessi.models import Security
from anncsu.common.sdk import BaseSDK


def _strict_do_request(
    self,
    hook_ctx,
    request,
    error_status_codes,
    stream: bool = False,
    retry_config: Optional[Tuple[Any, List[str]]] = None,
) -> httpx.Response:
    """Mirrors the real ``BaseSDK.do_request`` signature exactly.

    If the generated SDK passes any kwarg that is not in this signature
    (e.g. ``is_error_status_code``), Python raises ``TypeError`` before
    this body runs — that is the regression we want to catch.
    """
    return httpx.Response(
        200,
        request=httpx.Request("GET", "https://example.test/"),
        content=b'{"esito":"0","messaggio":"OK"}',
    )


@pytest.fixture
def accessi_sdk():
    return AnncsuAccessi(
        server_url="https://example.test",
        security=Security(),
    )


class TestAccessiDoRequestSignature:
    """Issue #26: generated SDK must call ``BaseSDK.do_request`` with the
    real signature (``error_status_codes`` list), not the Speakeasy 1.7+
    name (``is_error_status_code`` predicate)."""

    def test_show_status_calls_do_request_with_valid_kwargs(
        self, accessi_sdk, monkeypatch
    ):
        monkeypatch.setattr(BaseSDK, "do_request", _strict_do_request)
        try:
            accessi_sdk.status.show_status()
        except TypeError as e:
            if "is_error_status_code" in str(e):
                pytest.fail(f"show_status passed an invalid kwarg to do_request: {e}")
            raise
        except Exception:
            # Downstream unmarshalling may fail on the stub response —
            # we only care that do_request itself accepted the kwargs.
            pass

    def test_gestione_anncsu_pdnd_calls_do_request_with_valid_kwargs(
        self, accessi_sdk, monkeypatch
    ):
        monkeypatch.setattr(BaseSDK, "do_request", _strict_do_request)
        try:
            accessi_sdk.anncsu.gestione_anncsu_pdnd()
        except TypeError as e:
            if "is_error_status_code" in str(e):
                pytest.fail(
                    f"gestione_anncsu_pdnd passed an invalid kwarg to do_request: {e}"
                )
            raise
        except Exception:
            pass
