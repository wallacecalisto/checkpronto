
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Text, cast, or_  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402

_MARKERS = ("E2E", "Fase147")


def main() -> None:
    with SessionLocal() as db:
        conditions = []
        for marker in _MARKERS:
            conditions.append(AuditLog.actor_name.ilike(f"%{marker}%"))
            conditions.append(cast(AuditLog.before_data, Text).ilike(f"%{marker}%"))
            conditions.append(cast(AuditLog.after_data, Text).ilike(f"%{marker}%"))

        matches = db.query(AuditLog).filter(or_(*conditions)).all()

        if not matches:
            print("Nenhum log de teste E2E encontrado. Nada a fazer.")
            return

        print(f"Apagando {len(matches)} log(s) de auditoria gerados por testes E2E:")
        for entry in matches:
            print(f"  - #{entry.id} [{entry.entity_type}] {entry.actor_name} ({entry.action})")
            db.delete(entry)

        db.commit()
        print(f"OK: {len(matches)} log(s) removido(s).")


if __name__ == "__main__":
    main()
