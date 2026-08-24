"""Authorisation (REQ-013).

The permission matrix is declarative and lives in exactly one place, so a reviewer can
read it directly against the requirement rather than reconstructing it from scattered
checks. No service consults roles directly; every guard goes through ``require``.

Two properties this module must have, and how each is obtained:

* **Every refusal is recorded.** The audit write happens *before* the raise, so a refusal
  cannot be lost by an exception path that skips logging.
* **The customer-facing assistant holds no role at all.** It reaches only public
  endpoints, which is how REQ-013's "never any internal note, rating or gap entry"
  becomes structural rather than a matter of filtering responses correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.errors import PermissionDenied
from app.services.audit import AuditWriter


class Permission(StrEnum):
    ANSWER_USE_ASSIST = "answer.use_assist"
    CONVERSATION_HANDLE = "conversation.handle"
    FEEDBACK_SUBMIT = "feedback.submit"
    KNOWLEDGE_READ = "knowledge.read"
    KNOWLEDGE_WRITE = "knowledge.write"
    KNOWLEDGE_APPROVE = "knowledge.approve"
    KNOWLEDGE_RETIRE = "knowledge.retire"
    KNOWLEDGE_CLASSIFY = "knowledge.classify"
    GAPS_MANAGE = "gaps.manage"
    ANALYTICS_READ_ALL = "analytics.read_all"
    QUEUE_OVERRIDE = "queue.override"
    AUDIT_READ = "audit.read"
    ADMIN_USERS = "admin.users"
    ADMIN_THRESHOLDS = "admin.thresholds"
    ADMIN_LANGUAGES = "admin.languages"
    PRIVACY_DELETE = "privacy.delete"
    COVERAGE_DECLARE = "coverage.declare"


class Role(StrEnum):
    AGENT = "agent"
    KNOWLEDGE_MANAGER = "knowledge_manager"
    SUPERVISOR = "supervisor"
    ADMINISTRATOR = "administrator"


#: The matrix from lld-backend-pass3.md §4.3, verbatim.
#:
#: The agent row is exactly REQ-013's wording: "read approved knowledge, use assist,
#: submit feedback and gap entries, and nothing else."
PERMISSIONS_BY_ROLE: dict[Role, frozenset[Permission]] = {
    Role.AGENT: frozenset(
        {
            Permission.ANSWER_USE_ASSIST,
            Permission.CONVERSATION_HANDLE,
            Permission.FEEDBACK_SUBMIT,
            Permission.KNOWLEDGE_READ,
        }
    ),
    Role.KNOWLEDGE_MANAGER: frozenset(
        {
            Permission.ANSWER_USE_ASSIST,
            Permission.FEEDBACK_SUBMIT,
            Permission.KNOWLEDGE_READ,
            Permission.KNOWLEDGE_WRITE,
            Permission.KNOWLEDGE_APPROVE,
            Permission.KNOWLEDGE_RETIRE,
            Permission.KNOWLEDGE_CLASSIFY,
            Permission.GAPS_MANAGE,
            Permission.COVERAGE_DECLARE,
        }
    ),
    Role.SUPERVISOR: frozenset(
        {
            Permission.ANSWER_USE_ASSIST,
            Permission.FEEDBACK_SUBMIT,
            Permission.KNOWLEDGE_READ,
            Permission.ANALYTICS_READ_ALL,
            Permission.QUEUE_OVERRIDE,
            Permission.AUDIT_READ,
        }
    ),
    Role.ADMINISTRATOR: frozenset(Permission),
}


@dataclass(frozen=True)
class Actor:
    """Who is acting.

    ``user_id is None`` means unidentified — a public customer. REQ-013 requires
    identification before any role-bound action, so an unidentified actor fails every
    permission check by construction rather than by a check somebody must remember.
    """

    user_id: int | None
    roles: frozenset[Role]
    is_active: bool = True
    conversation_token: str | None = None

    @property
    def is_public(self) -> bool:
        return self.user_id is None

    @classmethod
    def public(cls, conversation_token: str | None = None) -> Actor:
        return cls(user_id=None, roles=frozenset(), conversation_token=conversation_token)


def permissions_of(roles: frozenset[Role]) -> frozenset[Permission]:
    """Union across roles — a knowledge manager who also takes conversations is a real
    staffing pattern, and forcing a second account would break attribution."""
    granted: set[Permission] = set()
    for role in roles:
        granted |= PERMISSIONS_BY_ROLE[role]
    return frozenset(granted)


class AuthorizationService:
    def __init__(self, audit: AuditWriter) -> None:
        self._audit = audit

    def require(self, actor: Actor, permission: Permission) -> None:
        """Raise PermissionDenied unless the actor holds the permission.

        Note the ordering: the refusal is audited *before* the raise (REQ-013).
        """
        if actor.user_id is None:
            self._record_refusal(actor, permission, "unidentified")
            raise PermissionDenied("unidentified")
        if not actor.is_active:
            self._record_refusal(actor, permission, "inactive")
            raise PermissionDenied("inactive")
        if permission not in permissions_of(actor.roles):
            self._record_refusal(actor, permission, "not_granted")
            raise PermissionDenied(permission.value)

    def has(self, actor: Actor, permission: Permission) -> bool:
        """Non-raising check for shaping a response.

        Deliberately does **not** audit: this answers "should this field be included",
        not "was an action refused", and auditing it would bury real refusals in noise.
        """
        return (
            actor.user_id is not None
            and actor.is_active
            and permission in permissions_of(actor.roles)
        )

    def _record_refusal(self, actor: Actor, permission: Permission, reason: str) -> None:
        self._audit.write(
            action="access_refused",
            subject_type="permission",
            subject_id=permission.value,
            actor_user_id=actor.user_id,
            actor_kind="public" if actor.is_public else "user",
            reason_code=reason,
        )
