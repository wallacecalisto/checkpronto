
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.task import DAYS_OF_WEEK, TaskExecutionHistory

ASSIGNMENTS_URL = "/api/v1/task-assignments"
TASKS_URL = "/api/v1/tasks"
PASSWORD = "SenhaForte123!"

_FAKE_IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"fake-jpeg-content" * 10  # só precisa "parecer" um arquivo, não ser um JPEG de verdade


def _today_day_of_week() -> str:
    return DAYS_OF_WEEK[datetime.now(timezone.utc).date().weekday()]


def _start_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/start"


def _complete_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/complete"


def _photo_url(assignment_id: int) -> str:
    return f"{ASSIGNMENTS_URL}/{assignment_id}/photo"


def _setup_scenario(make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof: bool):
    store = make_store()
    manager = make_user(email=f"gestor-pp-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Carlos", pin="1234")
    task = make_task(
        store_id=store.id,
        created_by_user_id=manager.id,
        title="Limpar a fritadeira",
        requires_photo_proof=requires_photo_proof,
    )
    assignment = make_task_assignment(task=task, day_of_week=_today_day_of_week(), sector_id=employee.sector_id)
    make_user(email=f"op-pp-{store.id}@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    return store, manager, employee, task, assignment, f"op-pp-{store.id}@kijapa.com"


# --- catálogo: requires_photo_proof --------------------------------------------------


def test_creates_task_with_requires_photo_proof(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-pp1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-pp1@kijapa.com", PASSWORD)

    response = client.post(
        TASKS_URL,
        json={"title": "Limpar a fritadeira", "requires_photo_proof": True},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["requires_photo_proof"] is True


def test_task_defaults_to_not_requiring_photo_proof(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-pp2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-pp2@kijapa.com", PASSWORD)

    response = client.post(TASKS_URL, json={"title": "Tarefa qualquer"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["requires_photo_proof"] is False


# --- validação backend: concluir como FEITO sem foto ---------------------------------


def test_completing_as_feito_without_photo_when_required_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "PHOTO_PROOF_REQUIRED"


def test_completing_as_nao_feito_without_photo_when_required_is_allowed(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "NAO_FEITO", "justification": "Faltou insumo."},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK


def test_task_without_photo_requirement_completes_normally(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=False
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK


# --- upload -----------------------------------------------------------------------


def test_uploads_photo_and_returns_a_url(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _photo_url(assignment.id),
        data={"employee_id": str(employee.id), "pin": "1234"},
        files={"photo": ("fritadeira.jpg", _FAKE_IMAGE_BYTES, "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    photo_url = response.json()["photo_url"]
    assert photo_url.startswith("https://pub-test.r2.dev/task-photos/")
    assert photo_url.endswith(".jpg")


def test_upload_rejects_non_image_content_type(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    response = client.post(
        _photo_url(assignment.id),
        data={"employee_id": str(employee.id), "pin": "1234"},
        files={"photo": ("relatorio.txt", b"nao sou uma imagem", "text/plain")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "INVALID_PHOTO"


def test_upload_requires_valid_pin(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)

    response = client.post(
        _photo_url(assignment.id),
        data={"employee_id": str(employee.id), "pin": "9999"},
        files={"photo": ("fritadeira.jpg", _FAKE_IMAGE_BYTES, "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["code"] == "PIN_INCORRECT"


# --- fluxo completo: upload -> completar -> histórico/timeline ----------------------


def test_full_flow_upload_then_complete_stores_photo_url_in_history(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    upload_response = client.post(
        _photo_url(assignment.id),
        data={"employee_id": str(employee.id), "pin": "1234"},
        files={"photo": ("fritadeira.jpg", _FAKE_IMAGE_BYTES, "image/jpeg")},
        headers=headers,
    )
    photo_url = upload_response.json()["photo_url"]

    complete_response = client.post(
        _complete_url(assignment.id),
        json={"employee_id": employee.id, "pin": "1234", "result": "FEITO", "photo_url": photo_url},
        headers=headers,
    )

    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.json()["photo_url"] == photo_url

    history = db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)).one()
    assert history.photo_url == photo_url

    gestor_headers = auth_headers(f"gestor-pp-{store.id}@kijapa.com", PASSWORD)
    timeline_response = client.get(f"/api/v1/task-execution-history/{history.id}/timeline", headers=gestor_headers)
    assert timeline_response.status_code == status.HTTP_200_OK
    assert timeline_response.json()["photo_url"] == photo_url


def test_completing_with_multiple_photos_stores_the_extras_in_history_and_timeline(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee, db_session
) -> None:
    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    client.post(_start_url(assignment.id), json={"employee_id": employee.id, "pin": "1234"}, headers=headers)

    photo_urls = []
    for filename in ("foto1.jpg", "foto2.jpg", "foto3.jpg"):
        upload_response = client.post(
            _photo_url(assignment.id),
            data={"employee_id": str(employee.id), "pin": "1234"},
            files={"photo": (filename, _FAKE_IMAGE_BYTES, "image/jpeg")},
            headers=headers,
        )
        photo_urls.append(upload_response.json()["photo_url"])

    complete_response = client.post(
        _complete_url(assignment.id),
        json={
            "employee_id": employee.id,
            "pin": "1234",
            "result": "FEITO",
            "photo_url": photo_urls[0],
            "extra_photo_urls": photo_urls[1:],
        },
        headers=headers,
    )

    assert complete_response.status_code == status.HTTP_200_OK
    assert complete_response.json()["photo_url"] == photo_urls[0]
    assert complete_response.json()["extra_photo_urls"] == photo_urls[1:]

    history = db_session.scalars(select(TaskExecutionHistory).where(TaskExecutionHistory.task_id == task.id)).one()
    assert history.extra_photo_urls == photo_urls[1:]

    gestor_headers = auth_headers(f"gestor-pp-{store.id}@kijapa.com", PASSWORD)
    timeline_response = client.get(f"/api/v1/task-execution-history/{history.id}/timeline", headers=gestor_headers)
    assert timeline_response.json()["extra_photo_urls"] == photo_urls[1:]


def test_photo_url_is_cleared_on_weekly_reset(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    from datetime import timedelta

    store, manager, employee, task, assignment, op_email = _setup_scenario(
        make_store, make_user, make_task, make_task_assignment, make_employee, requires_photo_proof=True
    )
    headers = auth_headers(op_email, PASSWORD)
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    stale_assignment = make_task_assignment(
        task=task,
        day_of_week=_today_day_of_week(),
        sector_id=employee.sector_id,
        status="COMPLETED",
        started_at=stale,
        completed_at=stale,
        completed_by_employee_id=employee.id,
        result="FEITO",
        photo_url="https://fake-storage.com/foto-antiga.jpg",
    )

    response = client.get(f"{ASSIGNMENTS_URL}/{stale_assignment.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["photo_url"] is None
