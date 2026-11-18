
from fastapi import status
from fastapi.testclient import TestClient

TEMPLATES_URL = "/api/v1/checklist-templates"
ITEMS_URL = "/api/v1/checklist-template-items"
PASSWORD = "SenhaForte123!"


def test_gestor_creates_template_with_items(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={
            "name": "Fechamento da cozinha",
            "shift": "Geral",
            "items": [
                {"description": "Desligar a fritadeira", "order_index": 0, "required": True},
                {"description": "Trancar a porta dos fundos", "order_index": 1, "required": False},
            ],
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["store_id"] == store.id
    assert body["active"] is True
    assert len(body["items"]) == 2
    assert body["items"][0]["description"] == "Desligar a fritadeira"
    assert body["items"][0]["required"] is True
    assert body["items"][1]["required"] is False


def test_operacional_cannot_create_template(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="op-ct1@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ct1@kijapa.com", PASSWORD)

    response = client.post(TEMPLATES_URL, json={"name": "X", "items": [{"description": "Item"}]}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_can_create_template(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="lider-ct1@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-ct1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL, json={"name": "X", "shift": "Geral", "items": [{"description": "Item"}]}, headers=headers
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_master_must_specify_store_to_create_template(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-ct1@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-ct1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL, json={"name": "X", "shift": "Geral", "items": [{"description": "Item"}]}, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "STORE_ID_REQUIRED"


def test_lider_and_operacional_can_list_templates(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Checklist Visível")
    make_user(email="lider-ct2@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    make_user(email="op-ct2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)

    for email in ("lider-ct2@kijapa.com", "op-ct2@kijapa.com"):
        headers = auth_headers(email, PASSWORD)
        response = client.get(TEMPLATES_URL, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        names = {t["name"] for t in response.json()}
        assert "Checklist Visível" in names


def test_active_only_filter(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Ativo", active=True)
    make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Inativo", active=False)
    headers = auth_headers("gestor-ct3@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}?active_only=true", headers=headers)

    names = {t["name"] for t in response.json()}
    assert names == {"Ativo"}


def test_get_template_includes_items_sorted_by_order_index(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Segundo", order_index=1)
    make_checklist_template_item(template=template, description="Primeiro", order_index=0)
    headers = auth_headers("gestor-ct4@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}/{template.id}", headers=headers)

    descriptions = [item["description"] for item in response.json()["items"]]
    assert descriptions == ["Primeiro", "Segundo"]


def test_gestor_cannot_view_template_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-ct@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    template_b = make_checklist_template(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_user(email="gestor-a-ct@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-ct@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}/{template_b.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_unknown_template_returns_404(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct404@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct404@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_gestor_edits_and_deactivates_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Nome Antigo")
    headers = auth_headers("gestor-ct5@kijapa.com", PASSWORD)

    response = client.patch(
        f"{TEMPLATES_URL}/{template.id}", json={"name": "Nome Novo", "active": False}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "Nome Novo"
    assert body["active"] is False


def test_lider_can_edit_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    """LIDER agora tem o mesmo acesso de edição que MASTER/GESTOR."""
    store = make_store()
    manager = make_user(email="gestor-ct6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_user(email="lider-ct6@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    headers = auth_headers("lider-ct6@kijapa.com", PASSWORD)

    response = client.patch(f"{TEMPLATES_URL}/{template.id}", json={"name": "Tentativa"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Tentativa"


def test_gestor_adds_item_to_existing_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-ct7@kijapa.com", PASSWORD)

    response = client.post(
        f"{TEMPLATES_URL}/{template.id}/items",
        json={"description": "Novo item", "order_index": 3, "required": False},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["template_id"] == template.id
    assert body["description"] == "Novo item"
    assert body["required"] is False


def test_gestor_edits_and_deactivates_item(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    item = make_checklist_template_item(template=template, description="Antigo")
    headers = auth_headers("gestor-ct8@kijapa.com", PASSWORD)

    response = client.patch(
        f"{ITEMS_URL}/{item.id}", json={"description": "Novo", "active": False}, headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["description"] == "Novo"
    assert body["active"] is False


def test_gestor_creates_template_with_shift(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct-shift1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct-shift1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={"name": "Fechamento", "shift": "Noite", "items": [{"description": "Item"}]},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["shift"] == "Noite"


def test_gestor_updates_template_shift(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-shift2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-ct-shift2@kijapa.com", PASSWORD)

    response = client.patch(f"{TEMPLATES_URL}/{template.id}", json={"shift": "Tarde"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["shift"] == "Tarde"


def test_creating_template_without_shift_is_rejected(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct-shift4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct-shift4@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL, json={"name": "Sem turno", "items": [{"description": "Item"}]}, headers=headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_gestor_creates_item_requiring_photo(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct-photo1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct-photo1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={
            "name": "Abertura",
            "shift": "Geral",
            "items": [{"description": "Foto da geladeira organizada", "requires_photo": True}],
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["items"][0]["requires_photo"] is True


def test_item_requires_photo_defaults_to_false(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-ct-photo2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct-photo2@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={"name": "Abertura", "shift": "Geral", "items": [{"description": "Item comum"}]},
        headers=headers,
    )

    assert response.json()["items"][0]["requires_photo"] is False


def test_gestor_toggles_requires_photo_on_existing_item(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-photo3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    item = make_checklist_template_item(template=template, requires_photo=False)
    headers = auth_headers("gestor-ct-photo3@kijapa.com", PASSWORD)

    response = client.patch(f"{ITEMS_URL}/{item.id}", json={"requires_photo": True}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requires_photo"] is True


def test_gestor_cannot_edit_item_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-ct2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    template_b = make_checklist_template(store_id=store_b.id, created_by_user_id=manager_b.id)
    item_b = make_checklist_template_item(template=template_b)
    make_user(email="gestor-a-ct2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-ct2@kijapa.com", PASSWORD)

    response = client.patch(f"{ITEMS_URL}/{item_b.id}", json={"description": "Tentativa"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_operacional_cannot_add_item(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_user(email="op-ct9@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-ct9@kijapa.com", PASSWORD)

    response = client.post(f"{TEMPLATES_URL}/{template.id}/items", json={"description": "X"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- DELETE /checklist-templates/{id} -------------------


def test_master_deletes_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-delete1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-ct-delete1@kijapa.com", password=PASSWORD, role="MASTER")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Vai ser excluído")
    headers = auth_headers("master-ct-delete1@kijapa.com", PASSWORD)

    response = client.delete(f"{TEMPLATES_URL}/{template.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False

    entries = client.get("/api/v1/audit", headers=headers).json()
    actions = {
        entry["action"]
        for entry in entries
        if entry["entity_id"] == template.id and entry["entity_type"] == "CHECKLIST_TEMPLATE"
    }
    assert "DELETE" in actions


def test_gestor_cannot_delete_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-delete2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("gestor-ct-delete2@kijapa.com", PASSWORD)

    response = client.delete(f"{TEMPLATES_URL}/{template.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_lider_cannot_delete_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-delete3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="lider-ct-delete@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    headers = auth_headers("lider-ct-delete@kijapa.com", PASSWORD)

    response = client.delete(f"{TEMPLATES_URL}/{template.id}", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_unknown_template_returns_404(client: TestClient, make_user, auth_headers) -> None:
    make_user(email="master-ct-delete2@kijapa.com", password=PASSWORD, role="MASTER")
    headers = auth_headers("master-ct-delete2@kijapa.com", PASSWORD)

    response = client.delete(f"{TEMPLATES_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_deleting_already_inactive_template_is_idempotent(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-delete4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-ct-delete3@kijapa.com", password=PASSWORD, role="MASTER")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, active=False)
    headers = auth_headers("master-ct-delete3@kijapa.com", PASSWORD)

    response = client.delete(f"{TEMPLATES_URL}/{template.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["active"] is False
    entries = client.get("/api/v1/audit", headers=headers).json()
    delete_logs = [
        entry
        for entry in entries
        if entry["entity_id"] == template.id
        and entry["entity_type"] == "CHECKLIST_TEMPLATE"
        and entry["action"] == "DELETE"
    ]
    assert len(delete_logs) == 0


def test_deleted_template_name_still_resolves_in_execution_history(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-delete5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    make_user(email="master-ct-delete4@kijapa.com", password=PASSWORD, role="MASTER")
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Fechamento")
    make_checklist_template_item(template=template)
    execution = make_checklist_execution(template=template, executed_by_user_id=manager.id)
    master_headers = auth_headers("master-ct-delete4@kijapa.com", PASSWORD)

    delete_response = client.delete(f"{TEMPLATES_URL}/{template.id}", headers=master_headers)
    assert delete_response.status_code == status.HTTP_200_OK

    gestor_headers = auth_headers("gestor-ct-delete5@kijapa.com", PASSWORD)
    response = client.get(f"/api/v1/checklists/{execution.id}", headers=gestor_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["template_name"] == "Fechamento"


# --- target_sector_id ---------------------------


def test_creates_template_with_target_sector(client: TestClient, make_user, auth_headers, make_store, make_sector) -> None:
    store = make_store()
    make_user(email="gestor-ct-sector1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector = make_sector(store_id=store.id, name="Cozinha Quente")
    headers = auth_headers("gestor-ct-sector1@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={
            "name": "Fechamento da cozinha",
            "shift": "Geral",
            "target_sector_id": sector.id,
            "items": [{"description": "Desligar a fritadeira"}],
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["target_sector_id"] == sector.id


def test_template_without_target_sector_is_a_management_checklist(
    client: TestClient, make_user, auth_headers, make_store
) -> None:
    store = make_store()
    make_user(email="gestor-ct-sector2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-ct-sector2@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={"name": "Checklist de gestão", "shift": "Geral", "items": [{"description": "Item 1"}]},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["target_sector_id"] is None


def test_cannot_create_template_with_sector_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    make_user(email="gestor-ct-sector3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    sector_b = make_sector(store_id=store_b.id)
    headers = auth_headers("gestor-ct-sector3@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={"name": "Checklist", "shift": "Geral", "target_sector_id": sector_b.id, "items": [{"description": "Item 1"}]},
        headers=headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_cannot_create_template_with_inactive_sector(
    client: TestClient, make_user, auth_headers, make_store, make_sector
) -> None:
    store = make_store()
    make_user(email="gestor-ct-sector4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector = make_sector(store_id=store.id, active=False)
    headers = auth_headers("gestor-ct-sector4@kijapa.com", PASSWORD)

    response = client.post(
        TEMPLATES_URL,
        json={"name": "Checklist", "shift": "Geral", "target_sector_id": sector.id, "items": [{"description": "Item 1"}]},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "SECTOR_INACTIVE"


def test_updating_target_sector_to_null_clears_it(
    client: TestClient, make_user, auth_headers, make_store, make_sector, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-sector5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector = make_sector(store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, target_sector_id=sector.id)
    headers = auth_headers("gestor-ct-sector5@kijapa.com", PASSWORD)

    response = client.patch(f"{TEMPLATES_URL}/{template.id}", json={"target_sector_id": None}, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["target_sector_id"] is None


def test_list_templates_filtered_by_sector_includes_sector_specific_and_general(
    client: TestClient, make_user, auth_headers, make_store, make_sector, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-ct-sector6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    sector_a = make_sector(store_id=store.id, name="Setor A")
    sector_b = make_sector(store_id=store.id, name="Setor B")
    make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, name="Do Setor A", target_sector_id=sector_a.id
    )
    make_checklist_template(
        store_id=store.id, created_by_user_id=manager.id, name="Do Setor B", target_sector_id=sector_b.id
    )
    make_checklist_template(store_id=store.id, created_by_user_id=manager.id, name="Geral (sem setor)")
    headers = auth_headers("gestor-ct-sector6@kijapa.com", PASSWORD)

    response = client.get(f"{TEMPLATES_URL}?sector_id={sector_a.id}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    names = {template["name"] for template in response.json()}
    assert names == {"Do Setor A", "Geral (sem setor)"}
