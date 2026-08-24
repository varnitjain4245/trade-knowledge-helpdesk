"""User and role repository (REQ-013).

Users are deactivated, never deleted: every audit record references an actor, and a
deleted user would orphan the attribution REQ-014 exists to preserve.

``count_active_administrators`` exists for one reason — a system whose last
administrator can be deactivated can be locked permanently, and that is not recoverable
in-product.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class AppUser:
    id: int
    external_id: str
    display_name: str
    email: str
    primary_language: str
    is_active: bool
    roles: frozenset[str] = field(default_factory=frozenset)
    working_languages: frozenset[str] = field(default_factory=frozenset)


_SELECT = """
    SELECT u.id, u.external_id, u.display_name, u.email, u.primary_language, u.is_active,
           COALESCE(array_agg(DISTINCT r.role) FILTER (WHERE r.role IS NOT NULL), '{}') AS roles,
           COALESCE(array_agg(DISTINCT al.language) FILTER (WHERE al.language IS NOT NULL), '{}')
               AS working_languages
      FROM app_user u
      LEFT JOIN user_role_grant r ON r.user_id = u.id
      LEFT JOIN agent_language al ON al.agent_id = u.id
"""


def _to_user(row) -> AppUser:  # type: ignore[no-untyped-def]
    return AppUser(
        id=row["id"], external_id=row["external_id"], display_name=row["display_name"],
        email=row["email"], primary_language=row["primary_language"],
        is_active=row["is_active"], roles=frozenset(row["roles"]),
        working_languages=frozenset(row["working_languages"]),
    )


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> AppUser | None:
        row = self._session.execute(
            text(_SELECT + " WHERE u.id = :id GROUP BY u.id"), {"id": user_id}
        ).mappings().first()
        return _to_user(row) if row else None

    def get_by_external_id(self, external_id: str) -> AppUser | None:
        row = self._session.execute(
            text(_SELECT + " WHERE u.external_id = :eid GROUP BY u.id"),
            {"eid": external_id},
        ).mappings().first()
        return _to_user(row) if row else None

    def create(
        self, external_id: str, display_name: str, email: str, primary_language: str
    ) -> int:
        return self._session.execute(
            text(
                """
                INSERT INTO app_user (external_id, display_name, email, primary_language)
                VALUES (:eid, :name, :email, :lang) RETURNING id
                """
            ),
            {"eid": external_id, "name": display_name, "email": email, "lang": primary_language},
        ).scalar_one()

    def grant_role(self, user_id: int, role: str, granted_by: int) -> None:
        self._session.execute(
            text(
                """
                INSERT INTO user_role_grant (user_id, role, granted_by)
                VALUES (:uid, :role, :by) ON CONFLICT DO NOTHING
                """
            ),
            {"uid": user_id, "role": role, "by": granted_by},
        )

    def revoke_role(self, user_id: int, role: str) -> None:
        self._session.execute(
            text("DELETE FROM user_role_grant WHERE user_id = :uid AND role = :role"),
            {"uid": user_id, "role": role},
        )

    def set_working_languages(self, agent_id: int, languages: list[str]) -> None:
        self._session.execute(
            text("DELETE FROM agent_language WHERE agent_id = :aid"), {"aid": agent_id}
        )
        for language in languages:
            self._session.execute(
                text("INSERT INTO agent_language (agent_id, language) VALUES (:aid, :lang)"),
                {"aid": agent_id, "lang": language},
            )

    def deactivate(self, user_id: int, by_user_id: int) -> None:
        self._session.execute(
            text(
                """
                UPDATE app_user
                   SET is_active = FALSE, deactivated_at = now(), deactivated_by = :by
                 WHERE id = :uid
                """
            ),
            {"uid": user_id, "by": by_user_id},
        )

    def count_active_administrators(self, excluding: int | None = None) -> int:
        """Counted under SERIALIZABLE by the caller.

        This is the one place in the design where a phantom read is genuinely dangerous:
        two concurrent deactivations could each observe one remaining administrator and
        both proceed, locking the system permanently.
        """
        return self._session.execute(
            text(
                """
                SELECT count(*) FROM app_user u
                  JOIN user_role_grant r ON r.user_id = u.id AND r.role = 'administrator'
                 WHERE u.is_active AND (:excluding IS NULL OR u.id <> :excluding)
                """
            ),
            {"excluding": excluding},
        ).scalar_one()
