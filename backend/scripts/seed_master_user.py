
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_secret  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    if not settings.master_user_email or not settings.master_user_password:
        print(
            "Defina MASTER_USER_EMAIL e MASTER_USER_PASSWORD em backend/.env "
            "antes de rodar este script (veja backend/.env.example)."
        )
        raise SystemExit(1)

    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == settings.master_user_email).one_or_none()
        if existing is not None:
            print(f"Usuário MASTER '{existing.email}' já existe (id={existing.id}). Nada a fazer.")
            return

        user = User(
            store_id=None,
            name=settings.master_user_name,
            email=settings.master_user_email,
            password_hash=hash_secret(settings.master_user_password),
            role="MASTER",
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Usuário MASTER criado: {user.email} (id={user.id}).")


if __name__ == "__main__":
    main()
