"""Business identity verification through API Setu.

Scheme eligibility currently rests on what somebody typed about themselves. That is
fine for guidance and wrong for entitlement: an enterprise told it qualifies for a
micro-enterprise credit guarantee on the strength of a self-declared turnover has been
told something the system cannot stand behind. Verification against the registry that
issued the identifier turns "seven schemes matched to what you told us" into "seven
schemes matched to your registered category".

API Setu is MeitY's aggregator over the departments that hold these registries. Two
identifiers matter here:

  Udyam   The MSME registration number. Carries the enterprise's micro/small/medium
          classification, which is the single input most scheme rules turn on.
  GSTIN   The GST identification number. Carries legal name and registration status,
          which is what customs and export schemes check.

Three properties this module holds to, each of which is a way the feature could
otherwise cause harm:

1. **Format checking is not verification.** A number can be well-formed and belong to
   nobody. The checksum functions here reject typos before a call is made; they never
   report a number as verified. Conflating the two would let anyone claim any category
   by typing a valid-looking number.

2. **An unreachable registry is not a failed verification.** If API Setu cannot be
   reached, the status is ``unavailable``, never ``invalid``. Telling a legitimate
   enterprise its registration is invalid because a government API was down is a worse
   error than not checking at all.

3. **Nothing verified is stored beyond what was checked.** The registry response is
   read for classification and status and then discarded. This system has no business
   holding a copy of the MSME register.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

APISETU_BASE = "https://apisetu.gov.in/api"

#: UDYAM-<2 letter state>-<2 digit>-<7 digit>
_UDYAM = re.compile(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$")

#: 2-digit state, 10-character PAN, 1 entity digit, 'Z', 1 checksum character.
_GSTIN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")

_GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

Status = Literal["verified", "invalid_format", "not_found", "unavailable"]

#: Turnover and investment ceilings that define the MSME classification. Recorded here
#: because scheme matching depends on them and a magic number in matching code cannot
#: be checked against the notification that set it.
MSME_CLASSES = {
    "micro": {"investment_cr": 1.0, "turnover_cr": 5.0},
    "small": {"investment_cr": 10.0, "turnover_cr": 50.0},
    "medium": {"investment_cr": 50.0, "turnover_cr": 250.0},
}


@dataclass(frozen=True)
class Verification:
    identifier: str
    kind: Literal["udyam", "gstin"]
    status: Status
    legal_name: str | None = None
    #: micro | small | medium, for Udyam only.
    classification: str | None = None
    state: str | None = None
    message: str = ""

    @property
    def trusted(self) -> bool:
        """Whether downstream logic may rely on this. Only a registry says yes."""
        return self.status == "verified"

    def as_dict(self) -> dict:
        return {
            "identifier": self.identifier, "kind": self.kind, "status": self.status,
            "trusted": self.trusted, "legal_name": self.legal_name,
            "classification": self.classification, "state": self.state,
            "message": self.message,
        }


def gstin_checksum_ok(gstin: str) -> bool:
    """The GSTIN's own check character, computed as the GSTN specification defines it.

    Catches a mistyped digit without a network call. It says the number is well-formed;
    it says nothing at all about whether it was ever issued.
    """
    if not _GSTIN.match(gstin):
        return False
    total = 0
    for i, char in enumerate(gstin[:14]):
        value = _GSTIN_ALPHABET.index(char)
        product = value * (2 if i % 2 else 1)
        total += product // 36 + product % 36
    return _GSTIN_ALPHABET[(36 - total % 36) % 36] == gstin[14]


def udyam_format_ok(number: str) -> bool:
    return bool(_UDYAM.match(number.strip().upper()))


class BusinessVerifier:
    def __init__(self, api_key: str = "", client_id: str = "") -> None:
        self._key = api_key
        self._client_id = client_id

    @property
    def available(self) -> bool:
        return bool(self._key and self._client_id)

    async def verify_udyam(self, number: str) -> Verification:
        number = number.strip().upper()
        if not udyam_format_ok(number):
            return Verification(
                number, "udyam", "invalid_format",
                message="A Udyam number looks like UDYAM-UP-12-1234567.",
            )
        if not self.available:
            return Verification(
                number, "udyam", "unavailable",
                message="The format is correct. The MSME registry is not connected, "
                        "so this has not been checked against it.",
            )
        return await self._call("udyam", number, f"{APISETU_BASE}/msme/v1/udyam/{number}")

    async def verify_gstin(self, gstin: str) -> Verification:
        gstin = gstin.strip().upper()
        if not gstin_checksum_ok(gstin):
            return Verification(
                gstin, "gstin", "invalid_format",
                message="That GSTIN fails its own check digit, so it contains a typo.",
            )
        if not self.available:
            return Verification(
                gstin, "gstin", "unavailable",
                message="The check digit is correct. The GST registry is not "
                        "connected, so this has not been checked against it.",
            )
        return await self._call("gstin", gstin, f"{APISETU_BASE}/gstn/v1/taxpayer/{gstin}")

    async def _call(self, kind: str, identifier: str, url: str) -> Verification:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    url,
                    headers={"X-APISETU-APIKEY": self._key,
                             "X-APISETU-CLIENTID": self._client_id},
                )
            if response.status_code == 404:
                return Verification(identifier, kind, "not_found",  # type: ignore[arg-type]
                                    message="No registration found with that number.")
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Deliberately not 'invalid'. A registry being down says nothing about the
            # enterprise, and reporting otherwise would accuse a legitimate business.
            log.warning("verify.unavailable", kind=kind, error=str(exc))
            return Verification(
                identifier, kind, "unavailable",  # type: ignore[arg-type]
                message="The registry could not be reached, so this has not been "
                        "checked. It has not been found invalid.",
            )

        classification = (body.get("enterpriseType") or body.get("classification") or "")
        return Verification(
            identifier=identifier, kind=kind,  # type: ignore[arg-type]
            status="verified",
            legal_name=body.get("legalName") or body.get("enterpriseName"),
            classification=classification.lower() or None,
            state=body.get("state"),
            message="Verified against the issuing registry.",
        )


def classify_by_turnover(turnover_cr: float | None,
                         investment_cr: float | None = None) -> str | None:
    """Self-declared classification, for when no registration has been verified.

    Kept separate from ``Verification`` on purpose: this is what somebody said about
    themselves, and the interface must not present it as though a registry confirmed it.
    """
    if turnover_cr is None and investment_cr is None:
        return None
    turnover = turnover_cr if turnover_cr is not None else 0.0
    investment = investment_cr if investment_cr is not None else 0.0
    for name, limits in MSME_CLASSES.items():
        if turnover <= limits["turnover_cr"] and investment <= limits["investment_cr"]:
            return name
    return "large"


def demo() -> None:
    """Self-check: the checksum, and the refusal to confuse 'unreachable' with 'invalid'."""
    import asyncio

    # A real, well-formed GSTIN check character. 27AAPFU0939F1ZV is the example used
    # in GSTN's own documentation.
    assert gstin_checksum_ok("27AAPFU0939F1ZV"), "valid GSTIN rejected"
    # Change one digit and the check character no longer agrees.
    assert not gstin_checksum_ok("27AAPFU0939F1ZX")
    assert not gstin_checksum_ok("27AAPFU0939F1Z")
    assert not gstin_checksum_ok("nonsense")

    assert udyam_format_ok("UDYAM-UP-12-1234567")
    assert udyam_format_ok("udyam-mh-01-0000001")
    assert not udyam_format_ok("UDYAM-UP-12-123")
    assert not udyam_format_ok("UP-12-1234567")

    verifier = BusinessVerifier()
    assert not verifier.available

    # Unconfigured must report 'unavailable' and must NOT report 'verified'.
    result = asyncio.run(verifier.verify_udyam("UDYAM-UP-12-1234567"))
    assert result.status == "unavailable", result.status
    assert not result.trusted, "an unchecked number must never be trusted"

    bad = asyncio.run(verifier.verify_gstin("27AAPFU0939F1ZX"))
    assert bad.status == "invalid_format" and not bad.trusted

    # Classification thresholds follow the MSME notification.
    assert classify_by_turnover(3.0) == "micro"
    assert classify_by_turnover(20.0) == "small"
    assert classify_by_turnover(100.0) == "medium"
    assert classify_by_turnover(900.0) == "large"
    assert classify_by_turnover(None) is None

    print("verification: checks passed, unreachable never reads as invalid")


if __name__ == "__main__":
    demo()
