
from fastapi import status
from fastapi.testclient import TestClient

PASSWORD = "SenhaForte123!"


def _settings_url(store_id: int) -> str:
    return f"/api/v1/stores/{store_id}/settings"


def test_store_without_any_configuration_uses_documented_defaults(
    client: TestClient, make_store, make_user, auth_headers
):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.get(_settings_url(store.id), headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body == {
        "store_id": store.id,
        "max_assignees_per_task": None,
        "operational_checklists_enabled": True,
        "auto_logout_minutes": 5,
        "hide_task_timer": False,
        "require_live_photo_only": False,
        "require_pin_on_complete": False,
        "enable_audio_alerts": False,
        "shifts": ["Geral"],
    }


def test_gestor_updates_settings_of_own_store(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(
        _settings_url(store.id),
        json={"max_assignees_per_task": 1, "operational_checklists_enabled": False},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["max_assignees_per_task"] == 1
    assert body["operational_checklists_enabled"] is False

    # E persiste de verdade — não só o corpo da resposta do PATCH.
    get_response = client.get(_settings_url(store.id), headers=headers)
    assert get_response.json() == body


def test_master_updates_settings_of_any_store(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email="master@kijapa.com", password=PASSWORD, role="MASTER", store_id=None)
    headers = auth_headers("master@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"max_assignees_per_task": 2}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["max_assignees_per_task"] == 2


def test_lider_cannot_update_settings(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"lider-{store.id}@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers(f"lider-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"max_assignees_per_task": 1}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_can_read_settings(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"lider-{store.id}@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers(f"lider-{store.id}@kijapa.com", PASSWORD)

    response = client.get(_settings_url(store.id), headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_settings_of_one_store_do_not_leak_into_another(client: TestClient, make_store, make_user, auth_headers):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master@kijapa.com", password=PASSWORD, role="MASTER", store_id=None)
    master_headers = auth_headers("master@kijapa.com", PASSWORD)
    client.patch(_settings_url(store_a.id), json={"max_assignees_per_task": 1}, headers=master_headers)

    make_user(email=f"gestor-{store_b.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    gestor_b_headers = auth_headers(f"gestor-{store_b.id}@kijapa.com", PASSWORD)

    response = client.get(_settings_url(store_b.id), headers=gestor_b_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["max_assignees_per_task"] is None  # padrão, não vazou o 1 da Loja A


def test_gestor_cannot_read_or_write_settings_of_another_store(
    client: TestClient, make_store, make_user, auth_headers
):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email=f"gestor-{store_a.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers(f"gestor-{store_a.id}@kijapa.com", PASSWORD)

    get_response = client.get(_settings_url(store_b.id), headers=headers)
    patch_response = client.patch(_settings_url(store_b.id), json={"max_assignees_per_task": 1}, headers=headers)

    assert get_response.status_code == status.HTTP_403_FORBIDDEN
    assert patch_response.status_code == status.HTTP_403_FORBIDDEN


def test_partial_update_does_not_reset_the_other_field(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)
    client.patch(_settings_url(store.id), json={"max_assignees_per_task": 3}, headers=headers)

    response = client.patch(_settings_url(store.id), json={"operational_checklists_enabled": False}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["max_assignees_per_task"] == 3
    assert body["operational_checklists_enabled"] is False


def test_explicit_null_resets_max_assignees_to_unlimited(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)
    client.patch(_settings_url(store.id), json={"max_assignees_per_task": 1}, headers=headers)

    response = client.patch(_settings_url(store.id), json={"max_assignees_per_task": None}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["max_assignees_per_task"] is None


def test_settings_update_endpoint_passes_cors_preflight(client: TestClient) -> None:
    response = client.options(
        "/api/v1/stores/1/settings",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_negative_max_assignees_is_rejected(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"max_assignees_per_task": -1}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_gestor_edits_shifts(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(
        _settings_url(store.id), json={"shifts": ["Abertura", "Fechamento"]}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["shifts"] == ["Abertura", "Fechamento"]

    get_response = client.get(_settings_url(store.id), headers=headers)
    assert get_response.json()["shifts"] == ["Abertura", "Fechamento"]


def test_empty_shifts_list_is_rejected(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"shifts": []}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_shifts_of_one_store_do_not_leak_into_another(client: TestClient, make_store, make_user, auth_headers):
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="master@kijapa.com", password=PASSWORD, role="MASTER", store_id=None)
    master_headers = auth_headers("master@kijapa.com", PASSWORD)
    client.patch(_settings_url(store_a.id), json={"shifts": ["Turno Único"]}, headers=master_headers)

    make_user(email=f"gestor-{store_b.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    gestor_b_headers = auth_headers(f"gestor-{store_b.id}@kijapa.com", PASSWORD)

    response = client.get(_settings_url(store_b.id), headers=gestor_b_headers)

    assert response.json()["shifts"] == ["Geral"]  # padrão, não vazou o da Loja A


def test_first_ever_patch_for_a_store_saves_max_assignees_one_correctly(
    client: TestClient, make_store, make_user, auth_headers
):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"max_assignees_per_task": 1}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["max_assignees_per_task"] == 1
    # Campos não enviados nesse primeiro PATCH recebem os padrões documentados,
    # não erro nem null indevido.
    assert body["auto_logout_minutes"] == 5
    assert body["operational_checklists_enabled"] is True


def test_upsert_preserves_untouched_new_fields_across_separate_patches(
    client: TestClient, make_store, make_user, auth_headers
):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)
    client.patch(_settings_url(store.id), json={"auto_logout_minutes": 10}, headers=headers)

    response = client.patch(_settings_url(store.id), json={"require_pin_on_complete": True}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["auto_logout_minutes"] == 10  # não foi resetado pro padrão (5)
    assert body["require_pin_on_complete"] is True


def test_updates_all_new_operational_flags(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(
        _settings_url(store.id),
        json={
            "auto_logout_minutes": 3,
            "hide_task_timer": True,
            "require_live_photo_only": True,
            "require_pin_on_complete": True,
            "enable_audio_alerts": True,
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["auto_logout_minutes"] == 3
    assert body["hide_task_timer"] is True
    assert body["require_live_photo_only"] is True
    assert body["require_pin_on_complete"] is True
    assert body["enable_audio_alerts"] is True


def test_auto_logout_minutes_below_one_is_rejected(client: TestClient, make_store, make_user, auth_headers):
    store = make_store()
    make_user(email=f"gestor-{store.id}@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers(f"gestor-{store.id}@kijapa.com", PASSWORD)

    response = client.patch(_settings_url(store.id), json={"auto_logout_minutes": 0}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
