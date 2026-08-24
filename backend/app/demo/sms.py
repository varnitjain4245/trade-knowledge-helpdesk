"""Sending a one-time code to a phone.

Delivery needs a provider account with credit — there is no way around that, and a
prototype that pretends otherwise teaches the wrong thing. So the sender is an interface
with three implementations:

* ``MSG91Sender``  — India's common choice, and it handles DLT template registration,
  which is mandatory for transactional SMS to Indian numbers.
* ``TwilioSender`` — used where the audience is not only Indian.
* ``ConsoleSender`` — the fallback when no provider is configured. It logs the code and
  returns it to the caller, **flagged as undelivered**, so the flow can be exercised
  end to end without anybody being misled into thinking a message was sent.

Set ``SCC_SMS_PROVIDER`` with the matching credentials to switch from the third to one of
the first two. Nothing else changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger(__name__)

#: Indian mobile numbers: ten digits beginning 6-9, optionally with the country code.
_INDIAN_MOBILE = re.compile(r"^(?:\+?91[\s-]?)?([6-9]\d{9})$")


def normalise_phone(raw: str) -> str | None:
    """Return the number in E.164, or None when it is not a valid Indian mobile.

    Rejecting early matters: a mistyped number does not fail loudly, it silently sends a
    code to a stranger, and the person waiting for it has no way to tell the difference.
    """
    match = _INDIAN_MOBILE.match((raw or "").strip().replace(" ", ""))
    return f"+91{match.group(1)}" if match else None


@dataclass(frozen=True)
class SendResult:
    delivered: bool
    detail: str
    #: Only ever populated by ConsoleSender, so the flow is usable without a provider.
    #: A real sender must never return the code — it would defeat the entire mechanism.
    code_for_display: str | None = None


class SmsSender(Protocol):
    name: str
    async def send_code(self, phone: str, code: str) -> SendResult: ...


class ConsoleSender:
    """No provider configured. Logs the code and hands it back, marked undelivered."""

    name = "console"

    async def send_code(self, phone: str, code: str) -> SendResult:
        log.info("sms.not_sent", phone=phone[-4:], reason="no provider configured")
        return SendResult(
            delivered=False,
            detail="No SMS provider is configured, so nothing was sent to your phone. "
                   "The code is shown here so you can continue.",
            code_for_display=code,
        )


class MSG91Sender:
    """MSG91 — widely used for Indian transactional SMS.

    Indian carriers require the message template to be registered under DLT before it
    will be delivered, so this sends against a template id rather than free text. A
    provider configured without a registered template will accept the request and the
    message will never arrive, which is the failure worth knowing about in advance.
    """

    name = "msg91"

    def __init__(self, settings: Settings) -> None:
        self._key = settings.msg91_auth_key
        self._template = settings.msg91_template_id
        self._sender = settings.sms_sender_id

    async def send_code(self, phone: str, code: str) -> SendResult:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://control.msg91.com/api/v5/otp",
                    headers={"authkey": self._key, "Content-Type": "application/json"},
                    json={
                        "template_id": self._template,
                        "mobile": phone.lstrip("+"),
                        "sender": self._sender,
                        "otp": code,
                    },
                )
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("sms.provider_error", provider=self.name, error=str(exc)[:140])
            return SendResult(False, "The SMS service could not be reached. Try again.")

        if response.status_code == 200 and body.get("type") == "success":
            return SendResult(True, f"Code sent to the number ending {phone[-4:]}.")
        log.warning("sms.rejected", provider=self.name, detail=str(body)[:160])
        return SendResult(False, "The SMS service rejected that number.")


class TwilioSender:
    name = "twilio"

    def __init__(self, settings: Settings) -> None:
        self._sid = settings.twilio_account_sid
        self._token = settings.twilio_auth_token
        self._from = settings.twilio_from_number

    async def send_code(self, phone: str, code: str) -> SendResult:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json",
                    auth=(self._sid, self._token),
                    data={
                        "To": phone, "From": self._from,
                        "Body": f"{code} is your Trade Knowledge Helpdesk verification "
                                f"code. It expires in 5 minutes. Do not share it.",
                    },
                )
        except httpx.HTTPError as exc:
            log.warning("sms.provider_error", provider=self.name, error=str(exc)[:140])
            return SendResult(False, "The SMS service could not be reached. Try again.")

        if response.status_code in (200, 201):
            return SendResult(True, f"Code sent to the number ending {phone[-4:]}.")
        log.warning("sms.rejected", provider=self.name, status=response.status_code)
        return SendResult(False, "The SMS service rejected that number.")


def build_sender(settings: Settings) -> SmsSender:
    provider = (settings.sms_provider or "").lower()
    if provider == "msg91" and settings.msg91_auth_key and settings.msg91_template_id:
        return MSG91Sender(settings)
    if provider == "twilio" and settings.twilio_account_sid and settings.twilio_auth_token:
        return TwilioSender(settings)
    if provider in ("msg91", "twilio"):
        # Named but incomplete. Saying so beats silently falling back and leaving someone
        # to wonder why no message arrives.
        log.warning("sms.provider_incomplete", provider=provider)
    return ConsoleSender()
