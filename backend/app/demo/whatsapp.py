"""WhatsApp as a channel into the same desk.

The National Consumer Helpline takes grievances on WhatsApp, by SMS, through the UMANG
app and on the web, and the redress system being built to replace CPGRAMS adds WhatsApp
filing and voice lodging. A trade helpdesk reachable only through a browser is reachable
by the subset of its users who have a browser, a stable connection and the confidence to
navigate a government portal — which is not the subset that most needs it.

This is a channel, not a second product. Every message goes through the same
``AnswerService``: the same citation rule, the same conflict ordering, the same refusal.
A channel that answered by a looser standard because the medium is casual would be the
worst thing this system could grow, since the person on WhatsApp has *less* ability to
check a claim than the person looking at the evidence panel, not more.

What changes with the medium is presentation, and one thing is worth stating plainly:
WhatsApp has no evidence panel, so the citation has to be inside the message. Every
answer sent here names its record, its issuing authority and its date in the body. An
answer whose provenance did not survive the trip to WhatsApp would be an uncited answer,
which this system does not produce on any channel.

Meta's Cloud API is the transport. Two obligations it imposes, both security-relevant:

  Webhook verification. Meta issues a GET with a challenge on registration, and the
  reply must echo it only when the verify token matches. Echoing unconditionally would
  let anyone point their own app at this endpoint.

  Signature checking. Every POST carries an X-Hub-Signature-256 HMAC over the raw body.
  It is checked here in constant time before the body is parsed. Without it, anyone who
  learns the URL can inject messages that appear to come from any phone number.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"

#: WhatsApp rejects a body over 4096 characters outright. Answers are trimmed to leave
#: room for the citation block, which is the part that must never be the bit that got cut.
BODY_LIMIT = 3500


@dataclass(frozen=True)
class InboundMessage:
    from_number: str
    text: str
    message_id: str
    #: 'text' | 'audio' | 'unsupported'
    kind: str = "text"
    audio_id: str | None = None


class WhatsAppChannel:
    def __init__(self, token: str = "", phone_number_id: str = "",
                 verify_token: str = "", app_secret: str = "") -> None:
        self._token = token
        self._phone_id = phone_number_id
        self._verify_token = verify_token
        self._app_secret = app_secret

    @property
    def available(self) -> bool:
        return bool(self._token and self._phone_id)

    # --- inbound ---------------------------------------------------------------------
    def verify(self, mode: str, token: str, challenge: str) -> str | None:
        """Answer Meta's registration challenge, only for the right token."""
        if mode == "subscribe" and token and token == self._verify_token:
            return challenge
        log.warning("whatsapp.verify_rejected", mode=mode)
        return None

    def signature_ok(self, raw_body: bytes, header: str | None) -> bool:
        """Constant-time HMAC check over the raw body.

        Returns False when no secret is configured. Not True: an unverifiable webhook
        is exactly the one an attacker would send, and defaulting to trust would make
        configuring the secret optional in practice.
        """
        if not self._app_secret or not header:
            return False
        if not header.startswith("sha256="):
            return False
        expected = hmac.new(
            self._app_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, header[len("sha256="):])

    @staticmethod
    def parse(payload: dict) -> list[InboundMessage]:
        """Pull messages out of Meta's envelope.

        Delivery receipts and status callbacks share this webhook and carry no message;
        they are skipped rather than treated as empty questions.
        """
        out: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    kind = message.get("type")
                    if kind == "text":
                        out.append(InboundMessage(
                            from_number=message.get("from", ""),
                            text=message.get("text", {}).get("body", "").strip(),
                            message_id=message.get("id", ""), kind="text"))
                    elif kind == "audio":
                        out.append(InboundMessage(
                            from_number=message.get("from", ""), text="",
                            message_id=message.get("id", ""), kind="audio",
                            audio_id=message.get("audio", {}).get("id")))
                    else:
                        out.append(InboundMessage(
                            from_number=message.get("from", ""), text="",
                            message_id=message.get("id", ""), kind="unsupported"))
        return out

    # --- outbound --------------------------------------------------------------------
    @staticmethod
    def render(result) -> str:  # noqa: ANN001
        """Format an AnswerResult for a medium with no evidence panel.

        The citation is inside the message because there is nowhere else to put it.
        """
        outcome = getattr(result.outcome, "value", str(result.outcome))

        if outcome == "conflict":
            lines = ["*The records disagree on this.*",
                     "Both are shown below. Neither has been chosen for you."]
            for c in result.citations[:2]:
                lines.append(f"\n— _{c.item_title}_ ({c.issuing_authority}, "
                             f"issued {c.issued_on})\n{c.passage[:400]}")
            lines.append("\nReply *AGENT* to be put through to a person.")
            return "\n".join(lines)

        if outcome != "answered":
            return ("I could not find a record that answers that, so I am not going to "
                    "guess.\n\nReply *AGENT* to reach a person, or *GRIEVANCE* to lodge "
                    "a formal complaint with a tracking reference.")

        body = (result.answer_text or "")[:BODY_LIMIT]
        lines = [body, "", "*Source*"]
        for c in result.citations[:3]:
            stale = " — _review pending_" if getattr(c, "review_pending", False) else ""
            lines.append(f"• {c.item_title} — {c.issuing_authority}, "
                         f"issued {c.issued_on}{stale}")
        lines.append("\n_Reply_ *WRONG* _if this did not answer your question._")
        return "\n".join(lines)

    async def send(self, to: str, text: str) -> bool:
        if not self.available:
            log.warning("whatsapp.not_configured")
            return False
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{GRAPH_BASE}/{self._phone_id}/messages",
                    headers={"Authorization": f"Bearer {self._token}"},
                    json={"messaging_product": "whatsapp", "to": to,
                          "type": "text",
                          "text": {"body": text[:4096], "preview_url": False}},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("whatsapp.send_failed", error=str(exc))
            return False
        return True

    async def fetch_audio(self, media_id: str) -> bytes | None:
        """Download a voice note so it can be transcribed like any other recording."""
        if not self.available:
            return None
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                head = await client.get(
                    f"{GRAPH_BASE}/{media_id}",
                    headers={"Authorization": f"Bearer {self._token}"})
                head.raise_for_status()
                url = head.json().get("url")
                if not url:
                    return None
                media = await client.get(
                    url, headers={"Authorization": f"Bearer {self._token}"})
                media.raise_for_status()
                return media.content
        except httpx.HTTPError as exc:
            log.warning("whatsapp.media_failed", error=str(exc))
            return None


def demo() -> None:
    """Self-check of the two security obligations and the citation-in-body rule."""
    from datetime import date
    from types import SimpleNamespace

    channel = WhatsAppChannel(verify_token="v-tok", app_secret="s3cret")

    assert channel.verify("subscribe", "v-tok", "12345") == "12345"
    assert channel.verify("subscribe", "wrong", "12345") is None
    assert channel.verify("unsubscribe", "v-tok", "12345") is None

    body = b'{"entry":[]}'
    good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert channel.signature_ok(body, good)
    assert not channel.signature_ok(body, "sha256=" + "0" * 64)
    assert not channel.signature_ok(b'{"entry":[1]}', good), "body change must invalidate"
    assert not channel.signature_ok(body, None)
    # No secret must never mean "trust it".
    assert not WhatsAppChannel().signature_ok(body, good)

    parsed = WhatsAppChannel.parse({"entry": [{"changes": [{"value": {"messages": [
        {"from": "919876543210", "id": "wamid.1", "type": "text",
         "text": {"body": " what is RoDTEP "}}]}}]}]})
    assert len(parsed) == 1 and parsed[0].text == "what is RoDTEP"

    # A status callback carries no message and must not become an empty question.
    assert WhatsAppChannel.parse({"entry": [{"changes": [{"value": {
        "statuses": [{"id": "wamid.1", "status": "delivered"}]}}]}]}) == []

    citation = SimpleNamespace(item_title="Importer Exporter Code",
                               issuing_authority="DGFT", issued_on=date(2024, 4, 1),
                               passage="p", review_pending=False)
    answered = SimpleNamespace(outcome="answered", answer_text="Apply on the DGFT portal.",
                               citations=[citation])
    rendered = WhatsAppChannel.render(answered)
    # The whole point: provenance survives the trip to a medium with no side panel.
    assert "Importer Exporter Code" in rendered and "DGFT" in rendered
    assert "2024-04-01" in rendered

    refused = SimpleNamespace(outcome="no_answer", answer_text=None, citations=[])
    assert "not going to guess" in WhatsAppChannel.render(refused)
    assert "GRIEVANCE" in WhatsAppChannel.render(refused)

    conflict = SimpleNamespace(outcome="conflict", answer_text=None,
                               citations=[citation, citation])
    assert "disagree" in WhatsAppChannel.render(conflict)

    print("whatsapp: checks passed, signature enforced and citations survive the channel")


if __name__ == "__main__":
    demo()
