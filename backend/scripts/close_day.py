
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.task_assignment_service import close_out_day  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        result = close_out_day(db)

        closed = result["closed_blocked"]
        skipped = result["skipped_pending"]

        if not closed and not skipped:
            print("Nenhum agendamento pendente ou impedido hoje. Nada a fazer.")
            return

        if closed:
            print(f"Fechados como 'Não Feito' (impedidos não retomados): {len(closed)} agendamento(s).")
            for assignment_id in closed:
                print(f"  - agendamento #{assignment_id}")
        if skipped:
            print(
                f"Ainda pendentes (nunca iniciados — sem funcionário pra atribuir histórico): "
                f"{len(skipped)} agendamento(s)."
            )
            for assignment_id in skipped:
                print(f"  - agendamento #{assignment_id}")


if __name__ == "__main__":
    main()
