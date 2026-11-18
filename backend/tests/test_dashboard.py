
from datetime import datetime, time, timedelta, timezone

from fastapi.testclient import TestClient

from app.models.task import DAYS_OF_WEEK

DASHBOARD_URL = "/api/v1/dashboard"
PASSWORD = "SenhaForte123!"

_NOW = datetime.now(timezone.utc)
_TODAY = _NOW.date()


def _in_period(hours_ago: int = 1) -> datetime:
    return _NOW - timedelta(hours=hours_ago)


def _outside_period(days_ago: int = 60) -> datetime:
    return _NOW - timedelta(days=days_ago)


def _completed_at_for_weekday(day_of_week: str) -> datetime:
    target_index = DAYS_OF_WEEK.index(day_of_week)
    delta = (_TODAY.weekday() - target_index) % 7
    target_date = _TODAY - timedelta(days=delta)
    return datetime.combine(target_date, time(12, 0), tzinfo=timezone.utc)


# --- /summary --------------------------------------------------------------------


def test_summary_pending_comes_from_current_assignment_state(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash1@kijapa.com", PASSWORD)

    make_task_assignment(task=task, day_of_week="MONDAY", sector_id=employee.sector_id, status="PENDING")
    make_task_assignment(
        task=task,
        day_of_week="TUESDAY",
        sector_id=employee.sector_id,
        status="IN_PROGRESS",
        started_at=_in_period(1),
        started_by_employee_id=employee.id,
    )

    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["pending_tasks"] == 2
    assert body["completed_tasks"] == 0
    assert body["total_tasks"] == 2
    assert body["completion_rate"] == 0.0


def test_summary_pending_tasks_reflects_weekly_reset_like_assignments_screen(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash-bug@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash-bug@kijapa.com", PASSWORD)

    today_day = DAYS_OF_WEEK[_TODAY.weekday()]
    stale_completed_at = _NOW - timedelta(days=10)
    make_task_assignment(
        task=task,
        day_of_week=today_day,
        sector_id=employee.sector_id,
        status="COMPLETED",
        started_at=stale_completed_at - timedelta(minutes=5),
        completed_at=stale_completed_at,
        completed_by_employee_id=employee.id,
        result="FEITO",
    )

    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    assert response.json()["pending_tasks"] == 1


def test_summary_pending_tasks_filtered_by_selected_day_of_week(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash14@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash14@kijapa.com", PASSWORD)

    today_day = DAYS_OF_WEEK[_TODAY.weekday()]
    other_day = DAYS_OF_WEEK[(_TODAY.weekday() + 1) % 7]

    make_task_assignment(task=task, day_of_week=today_day, sector_id=employee.sector_id, status="PENDING")
    make_task_assignment(task=task, day_of_week=other_day, sector_id=employee.sector_id, status="PENDING")

    response = client.get(
        f"{DASHBOARD_URL}/summary?start_date={_TODAY.isoformat()}&end_date={_TODAY.isoformat()}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["pending_tasks"] == 1


def test_summary_completed_tasks_come_from_execution_history_in_period(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_employee,
    make_task_execution_history,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash1b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash1b@kijapa.com", PASSWORD)

    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        task_title=task.title,
        employee_id=employee.id,
        started_at=_in_period(2),
        completed_at=_in_period(1),
    )
    # Fora do período: não deve contar.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        task_title=task.title,
        employee_id=employee.id,
        started_at=_outside_period(60),
        completed_at=_outside_period(59),
    )

    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["completed_tasks"] == 1
    assert body["pending_tasks"] == 0
    assert body["total_tasks"] == 1
    assert body["completion_rate"] == 100.0


def test_summary_excludes_nao_feito_from_completed_tasks(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_employee,
    make_task_execution_history,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash1c@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash1c@kijapa.com", PASSWORD)

    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        task_title=task.title,
        employee_id=employee.id,
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="FEITO",
    )
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        task_title=task.title,
        employee_id=employee.id,
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="NAO_FEITO",
        justification="Sem ingrediente.",
    )

    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["completed_tasks"] == 1
    assert body["total_tasks"] == 1
    assert body["completion_rate"] == 100.0


def test_summary_with_no_activity_has_zero_completion_rate(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="gestor-dash2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-dash2@kijapa.com", PASSWORD)

    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_tasks"] == 0
    assert body["pending_tasks"] == 0
    assert body["completed_tasks"] == 0
    assert body["completion_rate"] == 0.0
    assert body["checklist_divergent_count"] == 0


def test_summary_counts_divergent_validations_in_period(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
    make_checklist_execution_item,
    make_checklist_validation,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    lider = make_user(email="lider-dash3@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    template_item = make_checklist_template_item(template=template)
    execution = make_checklist_execution(template=template, executed_by_user_id=manager.id, status="COMPLETED")
    execution_item = make_checklist_execution_item(execution=execution, template_item=template_item, response="DIVERGENTE")

    # Divergência dentro do período (padrão: últimos 7 dias).
    make_checklist_validation(
        execution_item=execution_item, validated_by_user_id=lider.id, result="DIVERGENTE", justification="Encontrado errado."
    )

    headers = auth_headers("gestor-dash3@kijapa.com", PASSWORD)
    response = client.get(DASHBOARD_URL + "/summary", headers=headers)

    assert response.status_code == 200
    assert response.json()["checklist_divergent_count"] == 1


def test_summary_ignores_divergent_validation_outside_period(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
    make_checklist_execution_item,
    make_checklist_validation,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    lider = make_user(email="lider-dash4@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    template_item = make_checklist_template_item(template=template)
    execution = make_checklist_execution(template=template, executed_by_user_id=manager.id, status="COMPLETED")
    execution_item = make_checklist_execution_item(execution=execution, template_item=template_item, response="DIVERGENTE")

    make_checklist_validation(
        execution_item=execution_item,
        validated_by_user_id=lider.id,
        result="DIVERGENTE",
        justification="Antigo.",
        validated_at=_outside_period(60),
    )

    headers = auth_headers("gestor-dash4@kijapa.com", PASSWORD)
    # Período explícito e recente — não cobre a validação de 60 dias atrás.
    response = client.get(
        f"{DASHBOARD_URL}/summary?start_date={(_TODAY - timedelta(days=3)).isoformat()}&end_date={_TODAY.isoformat()}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["checklist_divergent_count"] == 0


# --- /ranking ------------------


def test_ranking_orders_by_speed_not_volume(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    fast_employee = make_employee(store_id=store.id, name="Rápido")
    slow_employee = make_employee(store_id=store.id, name="Devagar")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash5@kijapa.com", PASSWORD)

    # Funcionário rápido: 1 tarefa concluída em 10 minutos.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=fast_employee.id,
        task_title=task.title,
        started_at=_in_period(2),
        completed_at=_NOW - timedelta(hours=1, minutes=50),
        result="FEITO",
    )
    # Funcionário devagar: 3 tarefas concluídas em 2 horas cada (mais volume,
    # porém bem mais lento em média) — não deveria superar o rápido.
    for _ in range(3):
        make_task_execution_history(
            store_id=store.id,
            task_id=task.id,
            employee_id=slow_employee.id,
            task_title=task.title,
            started_at=_NOW - timedelta(hours=3),
            completed_at=_in_period(1),
            result="FEITO",
        )

    response = client.get(DASHBOARD_URL + "/ranking", headers=headers)

    assert response.status_code == 200
    body = response.json()
    names = [entry["employee_name"] for entry in body]
    assert names.index("Rápido") < names.index("Devagar")
    fast_entry = next(entry for entry in body if entry["employee_name"] == "Rápido")
    slow_entry = next(entry for entry in body if entry["employee_name"] == "Devagar")
    assert fast_entry["completed_count"] == 1
    assert fast_entry["avg_execution_seconds"] == 600.0
    assert slow_entry["completed_count"] == 3
    assert slow_entry["avg_execution_seconds"] == 7200.0
    # Nenhuma das duas tarefas tinha SLA configurado.
    assert fast_entry["on_time_count"] == 0
    assert fast_entry["late_count"] == 0
    assert fast_entry["on_time_rate"] is None


def test_ranking_respects_limit(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash6@kijapa.com", PASSWORD)

    for index in range(3):
        employee = make_employee(store_id=store.id, name=f"Funcionário {index}")
        make_task_execution_history(
            store_id=store.id,
            task_id=task.id,
            employee_id=employee.id,
            task_title=task.title,
            started_at=_in_period(2),
            completed_at=_in_period(1),
            result="FEITO",
        )

    response = client.get(DASHBOARD_URL + "/ranking?limit=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_ranking_filters_by_sector(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_task_execution_history,
    make_employee,
    make_sector,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash-sector@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sushi = make_sector(store_id=store.id, name="Sushi")
    atendimento = make_sector(store_id=store.id, name="Atendimento")
    sushi_employee = make_employee(store_id=store.id, sector_id=sushi.id, name="Do Sushi")
    atendimento_employee = make_employee(store_id=store.id, sector_id=atendimento.id, name="Do Atendimento")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash-sector@kijapa.com", PASSWORD)

    for employee in (sushi_employee, atendimento_employee):
        make_task_execution_history(
            store_id=store.id,
            task_id=task.id,
            employee_id=employee.id,
            task_title=task.title,
            started_at=_in_period(2),
            completed_at=_in_period(1),
            result="FEITO",
        )

    response = client.get(f"{DASHBOARD_URL}/ranking?sector_id={sushi.id}", headers=headers)

    assert response.status_code == 200
    names = [entry["employee_name"] for entry in response.json()]
    assert names == ["Do Sushi"]


def test_ranking_employee_without_sla_has_null_on_time_rate(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash7@kijapa.com", PASSWORD)

    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="FEITO",
        estimated_duration_minutes=None,
    )

    response = client.get(DASHBOARD_URL + "/ranking", headers=headers)

    assert response.status_code == 200
    entry = response.json()[0]
    assert entry["completed_count"] == 1
    assert entry["avg_execution_seconds"] == 3600.0
    assert entry["on_time_count"] == 0
    assert entry["late_count"] == 0
    assert entry["on_time_rate"] is None


def test_ranking_excludes_nao_feito_from_math(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash17@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Com Falso Positivo")
    only_nao_feito_employee = make_employee(store_id=store.id, name="Só Não Feito")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, estimated_duration_minutes=30)
    headers = auth_headers("gestor-dash17@kijapa.com", PASSWORD)

    # Conclusão de verdade: 20 minutos, no prazo.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=_NOW - timedelta(hours=2, minutes=20),
        completed_at=_NOW - timedelta(hours=2),
        result="FEITO",
        estimated_duration_minutes=30,
    )
    # NAO_FEITO abandonada em 10 segundos — sem o filtro, isso derrubaria a
    # média de 20min pra ~5min e ainda contaria como "no prazo" no SLA.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=_in_period(1),
        completed_at=_in_period(1) + timedelta(seconds=10),
        result="NAO_FEITO",
        justification="Faltou material.",
        estimated_duration_minutes=30,
    )
    # Funcionário só com NAO_FEITO: não deve aparecer no ranking.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=only_nao_feito_employee.id,
        task_title=task.title,
        started_at=_in_period(1),
        completed_at=_in_period(1) + timedelta(seconds=5),
        result="NAO_FEITO",
        justification="Equipamento quebrado.",
    )

    response = client.get(DASHBOARD_URL + "/ranking", headers=headers)

    assert response.status_code == 200
    body = response.json()
    names = [entry["employee_name"] for entry in body]
    assert "Com Falso Positivo" in names
    assert "Só Não Feito" not in names

    entry = next(item for item in body if item["employee_name"] == "Com Falso Positivo")
    assert entry["completed_count"] == 1
    assert entry["avg_execution_seconds"] == 1200.0
    assert entry["on_time_count"] == 1
    assert entry["late_count"] == 0
    assert entry["on_time_rate"] == 100.0


# --- /weekly-trend -------------


def test_weekly_trend_buckets_avg_execution_time_by_day_of_week(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash8@kijapa.com", PASSWORD)

    monday_completed_at = _completed_at_for_weekday("MONDAY")
    # Segunda: uma conclusão de 20min e outra de 40min — média de 30min.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=monday_completed_at - timedelta(minutes=20),
        completed_at=monday_completed_at,
        result="FEITO",
    )
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=monday_completed_at - timedelta(minutes=40),
        completed_at=monday_completed_at,
        result="FEITO",
    )

    response = client.get(DASHBOARD_URL + "/weekly-trend", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [point["day_of_week"] for point in body] == [
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
        "SUNDAY",
    ]
    monday = next(point for point in body if point["day_of_week"] == "MONDAY")
    friday = next(point for point in body if point["day_of_week"] == "FRIDAY")
    assert monday["completed_count"] == 2
    assert monday["avg_execution_seconds"] == 1800.0
    assert friday["completed_count"] == 0
    assert friday["avg_execution_seconds"] is None


def test_weekly_trend_excludes_nao_feito(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash18@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash18@kijapa.com", PASSWORD)

    monday_completed_at = _completed_at_for_weekday("MONDAY")
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=monday_completed_at - timedelta(minutes=20),
        completed_at=monday_completed_at,
        result="FEITO",
    )
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title=task.title,
        started_at=monday_completed_at - timedelta(seconds=10),
        completed_at=monday_completed_at,
        result="NAO_FEITO",
        justification="Sem tempo.",
    )

    response = client.get(DASHBOARD_URL + "/weekly-trend", headers=headers)

    assert response.status_code == 200
    monday = next(point for point in response.json() if point["day_of_week"] == "MONDAY")
    assert monday["completed_count"] == 1
    assert monday["avg_execution_seconds"] == 1200.0


# --- restrição de papel e isolamento multi-loja -------------------------------------


def test_operacional_cannot_access_dashboard(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="op-dash1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-dash1@kijapa.com", PASSWORD)

    for path in (
        "/summary",
        "/ranking",
        "/weekly-trend",
        "/employees/999999/profile",
        "/activity-feed",
        "/exceptions",
        "/recent-checklists",
    ):
        response = client.get(DASHBOARD_URL + path, headers=headers)
        assert response.status_code == 403, path


def test_gestor_only_sees_own_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_assignment, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_a = make_user(email="gestor-a-dash9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    manager_b = make_user(email="gestor-b-dash9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    employee_b = make_employee(store_id=store_b.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_task_assignment(
        task=task_b,
        day_of_week="MONDAY",
        sector_id=employee_b.sector_id,
        status="COMPLETED",
        started_at=_in_period(2),
        completed_at=_in_period(1),
        completed_by_employee_id=employee_b.id,
        result="FEITO",
    )

    headers_a = auth_headers("gestor-a-dash9@kijapa.com", PASSWORD)
    response = client.get(DASHBOARD_URL + "/summary", headers=headers_a)

    assert response.status_code == 200
    assert response.json()["total_tasks"] == 0


def test_master_sees_all_stores_and_can_filter_by_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master-dash9@kijapa.com", password=PASSWORD, role="MASTER")
    manager_a = make_user(email="gestor-a-dash10@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    manager_b = make_user(email="gestor-b-dash10@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    employee_a = make_employee(store_id=store_a.id)
    employee_b = make_employee(store_id=store_b.id)
    task_a = make_task(store_id=store_a.id, created_by_user_id=manager_a.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    for store, task, employee in ((store_a, task_a, employee_a), (store_b, task_b, employee_b)):
        make_task_execution_history(
            store_id=store.id,
            task_id=task.id,
            task_title=task.title,
            employee_id=employee.id,
            started_at=_in_period(2),
            completed_at=_in_period(1),
        )

    headers = auth_headers("master-dash9@kijapa.com", PASSWORD)

    all_stores = client.get(DASHBOARD_URL + "/summary", headers=headers)
    assert all_stores.json()["total_tasks"] == 2

    only_a = client.get(f"{DASHBOARD_URL}/summary?store_id={store_a.id}", headers=headers)
    assert only_a.json()["total_tasks"] == 1


# --- /employees/{id}/profile --------------------


def test_employee_profile_returns_history_and_sla_breakdown(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash11@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Funcionária Exemplo")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, estimated_duration_minutes=30)
    headers = auth_headers("gestor-dash11@kijapa.com", PASSWORD)

    # No prazo (20min de 30 permitidos).
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Fazer 150 filadélfias",
        started_at=_NOW - timedelta(hours=2, minutes=20),
        completed_at=_NOW - timedelta(hours=2),
        result="FEITO",
        estimated_duration_minutes=30,
    )
    # Com atraso (45min de 30 permitidos).
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Lavar louça",
        started_at=_in_period(1) - timedelta(minutes=45),
        completed_at=_in_period(1),
        result="FEITO",
        estimated_duration_minutes=30,
    )

    response = client.get(f"{DASHBOARD_URL}/employees/{employee.id}/profile", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == employee.id
    assert body["employee_name"] == "Funcionária Exemplo"
    assert body["completed_count"] == 2
    assert body["on_time_count"] == 1
    assert body["late_count"] == 1
    assert body["on_time_rate"] == 50.0
    assert len(body["tasks"]) == 2
    # Mais recente primeiro.
    assert body["tasks"][0]["task_title"] == "Lavar louça"
    assert body["tasks"][0]["on_time"] is False
    assert body["tasks"][1]["task_title"] == "Fazer 150 filadélfias"
    assert body["tasks"][1]["on_time"] is True
    assert body["tasks"][1]["estimated_duration_minutes"] == 30


def test_employee_profile_excludes_nao_feito_from_stats_but_keeps_it_in_task_list(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash19@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Funcionário com Exceção")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, estimated_duration_minutes=30)
    headers = auth_headers("gestor-dash19@kijapa.com", PASSWORD)

    # No prazo (20min de 30 permitidos) — a única linha que deve valer pra matemática.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Fazer 150 filadélfias",
        started_at=_NOW - timedelta(hours=2, minutes=20),
        completed_at=_NOW - timedelta(hours=2),
        result="FEITO",
        estimated_duration_minutes=30,
    )
    # NAO_FEITO abandonada em 10s — não pode contar, mas precisa aparecer na lista.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Limpar fritadeira",
        started_at=_in_period(1),
        completed_at=_in_period(1) + timedelta(seconds=10),
        result="NAO_FEITO",
        justification="Fritadeira quebrada.",
        estimated_duration_minutes=30,
    )

    response = client.get(f"{DASHBOARD_URL}/employees/{employee.id}/profile", headers=headers)

    assert response.status_code == 200
    body = response.json()
    # Matemática: só a linha FEITO conta.
    assert body["completed_count"] == 1
    assert body["on_time_count"] == 1
    assert body["late_count"] == 0
    assert body["on_time_rate"] == 100.0
    # Auditoria: as DUAS linhas aparecem na lista de tarefas.
    assert len(body["tasks"]) == 2
    nao_feito_task = next(task for task in body["tasks"] if task["task_title"] == "Limpar fritadeira")
    assert nao_feito_task["result"] == "NAO_FEITO"
    assert nao_feito_task["justification"] == "Fritadeira quebrada."
    # Sem selo de "no prazo"/"com atraso" numa tarefa que não foi feita.
    assert nao_feito_task["on_time"] is None


def test_employee_profile_gestor_from_another_store_is_forbidden(
    client: TestClient, make_user, auth_headers, make_store, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="gestor-a-dash11@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    employee_b = make_employee(store_id=store_b.id)
    headers = auth_headers("gestor-a-dash11@kijapa.com", PASSWORD)

    response = client.get(f"{DASHBOARD_URL}/employees/{employee_b.id}/profile", headers=headers)

    assert response.status_code == 403


def test_employee_profile_unknown_employee_returns_404(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="gestor-dash12@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-dash12@kijapa.com", PASSWORD)

    response = client.get(f"{DASHBOARD_URL}/employees/999999/profile", headers=headers)

    assert response.status_code == 404


# --- /activity-feed ----------------------------------


def test_activity_feed_merges_task_and_checklist_events_sorted_by_time(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_task_execution_history,
    make_employee,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
    make_checklist_execution_item,
    make_checklist_validation,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="João")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    template_item = make_checklist_template_item(template=template)
    execution = make_checklist_execution(template=template, executed_by_user_id=manager.id, status="COMPLETED")
    execution_item = make_checklist_execution_item(execution=execution, template_item=template_item, response="OK")
    headers = auth_headers("gestor-dash13@kijapa.com", PASSWORD)

    # Conclusão de tarefa há 2 horas, validação de checklist há 1 hora (mais recente).
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Fazer 150 filadélfias",
        started_at=_NOW - timedelta(hours=2, minutes=10),
        completed_at=_NOW - timedelta(hours=2),
        result="FEITO",
    )
    make_checklist_validation(
        execution_item=execution_item,
        validated_by_user_id=manager.id,
        result="APROVADO",
        validated_at=_NOW - timedelta(hours=1),
    )
    # Ontem — não deve aparecer no feed (sempre "hoje").
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Tarefa de Ontem",
        started_at=_NOW - timedelta(days=1, hours=2),
        completed_at=_NOW - timedelta(days=1),
        result="FEITO",
    )

    response = client.get(DASHBOARD_URL + "/activity-feed", headers=headers)

    assert response.status_code == 200
    body = response.json()
    descriptions = [entry["description"] for entry in body]
    assert "Tarefa de Ontem" not in " ".join(descriptions)
    assert len(body) == 2
    # Mais recente primeiro: a validação (1h atrás) antes da conclusão de tarefa (2h atrás).
    assert body[0]["description"] == "validou um item de checklist"
    assert body[0]["actor_name"] == manager.name
    assert body[1]["description"] == 'concluiu "Fazer 150 filadélfias"'
    assert body[1]["actor_name"] == "João"


def test_activity_feed_master_can_filter_by_store(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    master = make_user(email="master-dash13@kijapa.com", password=PASSWORD, role="MASTER")
    manager_a = make_user(email="gestor-a-dash13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    manager_b = make_user(email="gestor-b-dash13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    employee_a = make_employee(store_id=store_a.id)
    employee_b = make_employee(store_id=store_b.id)
    task_a = make_task(store_id=store_a.id, created_by_user_id=manager_a.id)
    task_b = make_task(store_id=store_b.id, created_by_user_id=manager_b.id)
    for task, employee in ((task_a, employee_a), (task_b, employee_b)):
        make_task_execution_history(
            store_id=task.store_id,
            task_id=task.id,
            employee_id=employee.id,
            task_title=task.title,
            started_at=_in_period(1) - timedelta(minutes=10),
            completed_at=_in_period(1),
            result="FEITO",
        )

    headers = auth_headers("master-dash13@kijapa.com", PASSWORD)

    all_stores = client.get(DASHBOARD_URL + "/activity-feed", headers=headers)
    assert len(all_stores.json()) == 2

    only_a = client.get(f"{DASHBOARD_URL}/activity-feed?store_id={store_a.id}", headers=headers)
    assert len(only_a.json()) == 1


def test_activity_feed_accepts_explicit_period_for_ver_todos(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash-feed-period@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id)
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Tarefa de Ontem",
        started_at=_NOW - timedelta(days=1, hours=2),
        completed_at=_NOW - timedelta(days=1),
        result="FEITO",
    )

    headers = auth_headers("gestor-dash-feed-period@kijapa.com", PASSWORD)
    yesterday = (_NOW - timedelta(days=1)).date().isoformat()
    response = client.get(
        f"{DASHBOARD_URL}/activity-feed?start_date={yesterday}&end_date={yesterday}", headers=headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- /exceptions --------------------------------


def test_exceptions_lists_nao_feito_and_tasks_with_observation(
    client: TestClient, make_user, auth_headers, make_store, make_task, make_task_execution_history, make_employee
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash14@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    employee = make_employee(store_id=store.id, name="Funcionário Exceção")
    task = make_task(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-dash14@kijapa.com", PASSWORD)

    # "Não foi possível" — sempre com justificativa (regra já existente na tela operacional).
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Limpar fritadeira",
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="NAO_FEITO",
        justification="Fritadeira quebrada.",
    )
    # Concluída normalmente, mas com uma observação livre.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Organizar estoque",
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="FEITO",
        observation="Faltou 1 caixa de guardanapos.",
    )
    # Concluída normalmente, sem nenhuma observação — não deve aparecer.
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        employee_id=employee.id,
        task_title="Tarefa sem problema nenhum",
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="FEITO",
    )

    response = client.get(DASHBOARD_URL + "/exceptions", headers=headers)

    assert response.status_code == 200
    body = response.json()
    titles = [entry["title"] for entry in body]
    assert "Limpar fritadeira" in titles
    assert "Organizar estoque" in titles
    assert "Tarefa sem problema nenhum" not in titles

    nao_feito_entry = next(entry for entry in body if entry["title"] == "Limpar fritadeira")
    assert nao_feito_entry["type"] == "TAREFA"
    assert nao_feito_entry["reason"] == "Fritadeira quebrada."
    assert nao_feito_entry["user_name"] == "Funcionário Exceção"

    observation_entry = next(entry for entry in body if entry["title"] == "Organizar estoque")
    assert observation_entry["type"] == "TAREFA"
    assert observation_entry["reason"] == "Faltou 1 caixa de guardanapos."


def test_exceptions_lists_divergent_checklist_items(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
    make_checklist_execution_item,
    make_checklist_validation,
) -> None:
    store = make_store()
    executor = make_user(email="executor-dash21@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    validator = make_user(email="validador-dash21@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=executor.id, name="Fechamento")
    template_item = make_checklist_template_item(template=template, description="Desligar a fritadeira")
    execution = make_checklist_execution(template=template, executed_by_user_id=executor.id)
    execution_item = make_checklist_execution_item(
        execution=execution, template_item=template_item, response="DIVERGENTE"
    )
    # Item aprovado — não deve aparecer nos alertas.
    ok_item = make_checklist_execution_item(execution=execution, template_item=template_item, response="OK")
    make_checklist_validation(
        execution_item=ok_item, validated_by_user_id=validator.id, result="APROVADO", validated_at=_in_period(1)
    )
    make_checklist_validation(
        execution_item=execution_item,
        validated_by_user_id=validator.id,
        result="DIVERGENTE",
        justification="Fritadeira ficou ligada.",
        validated_at=_in_period(1),
    )

    headers = auth_headers("executor-dash21@kijapa.com", PASSWORD)
    response = client.get(DASHBOARD_URL + "/exceptions", headers=headers)

    assert response.status_code == 200
    body = response.json()
    checklist_entries = [entry for entry in body if entry["type"] == "CHECKLIST"]
    assert len(checklist_entries) == 1
    entry = checklist_entries[0]
    assert entry["title"] == "Desligar a fritadeira"
    assert entry["user_name"] == executor.name
    assert entry["reason"] == "Fritadeira ficou ligada."


# --- /recent-checklists ------------------------------------------------


def test_recent_checklists_includes_executor_and_validator_names(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
    make_checklist_execution_item,
    make_checklist_validation,
) -> None:
    store = make_store()
    executor = make_user(email="executor-dash15@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    validator = make_user(email="validador-dash15@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=executor.id, name="Fechamento")
    template_item = make_checklist_template_item(template=template)
    execution = make_checklist_execution(
        template=template, executed_by_user_id=executor.id, status="COMPLETED", finished_at=_in_period(1)
    )
    execution_item = make_checklist_execution_item(execution=execution, template_item=template_item, response="OK")
    make_checklist_validation(execution_item=execution_item, validated_by_user_id=validator.id, result="APROVADO")

    headers = auth_headers("executor-dash15@kijapa.com", PASSWORD)
    response = client.get(DASHBOARD_URL + "/recent-checklists", headers=headers)

    assert response.status_code == 200
    body = response.json()
    entry = next(item for item in body if item["id"] == execution.id)
    assert entry["template_name"] == "Fechamento"
    assert entry["executed_by_name"] == executor.name
    assert entry["validated_by_names"] == [validator.name]
    assert entry["fully_validated"] is True


def test_recent_checklists_respects_limit(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_execution,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash16@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    for _ in range(3):
        make_checklist_execution(template=template, executed_by_user_id=manager.id)

    headers = auth_headers("gestor-dash16@kijapa.com", PASSWORD)
    response = client.get(f"{DASHBOARD_URL}/recent-checklists?limit=2", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_recent_checklists_filters_by_period_when_provided(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_execution,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash-period@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_execution(template=template, executed_by_user_id=manager.id, started_at=_in_period(2))
    make_checklist_execution(
        template=template, executed_by_user_id=manager.id, started_at=_NOW - timedelta(days=30)
    )

    headers = auth_headers("gestor-dash-period@kijapa.com", PASSWORD)
    today = _NOW.date().isoformat()
    response = client.get(
        f"{DASHBOARD_URL}/recent-checklists?start_date={today}&end_date={today}", headers=headers
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# --- resiliência do BI a exclusões do catálogo -----------------------


def test_ranking_and_exceptions_show_deleted_task_title_normally(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_task,
    make_employee,
    make_task_execution_history,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-dash20@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-dash20@kijapa.com", password=PASSWORD, role="MASTER")
    employee = make_employee(store_id=store.id, name="Funcionária BI")
    task = make_task(store_id=store.id, created_by_user_id=manager.id, title="Tarefa Efêmera")
    make_task_execution_history(
        store_id=store.id,
        task_id=task.id,
        task_title=task.title,
        employee_id=employee.id,
        started_at=_in_period(2),
        completed_at=_in_period(1),
        result="NAO_FEITO",
        justification="Sem tempo.",
    )

    master_headers = auth_headers("master-dash20@kijapa.com", PASSWORD)
    delete_response = client.delete(f"/api/v1/tasks/{task.id}", headers=master_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["active"] is False

    gestor_headers = auth_headers("gestor-dash20@kijapa.com", PASSWORD)
    exceptions_response = client.get(DASHBOARD_URL + "/exceptions", headers=gestor_headers)
    assert exceptions_response.status_code == 200
    exception_titles = [entry["title"] for entry in exceptions_response.json()]
    assert "Tarefa Efêmera" in exception_titles
