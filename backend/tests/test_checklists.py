
from datetime import datetime, timedelta, timezone

from fastapi import status
from fastapi.testclient import TestClient

CHECKLISTS_URL = "/api/v1/checklists"
PASSWORD = "SenhaForte123!"


def _start_url() -> str:
    return CHECKLISTS_URL


def _item_url(execution_id: int, item_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/items/{item_id}"


def _complete_url(execution_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/complete"


def _validate_url(execution_id: int, item_id: int) -> str:
    return f"{CHECKLISTS_URL}/{execution_id}/items/{item_id}/validate"


# --- iniciar --------------------------------------------------------------------


def test_gestor_starts_execution_as_manager(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Item 1", order_index=0)
    make_checklist_template_item(template=template, description="Item 2", order_index=1)
    headers = auth_headers("gestor-cl1@kijapa.com", PASSWORD)

    response = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["executed_by_user_id"] == manager.id
    assert len(body["items"]) == 2
    assert {item["item_description_snapshot"] for item in body["items"]} == {"Item 1", "Item 2"}
    assert all(item["response"] is None for item in body["items"])


def test_operacional_cannot_start_execution(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Item 1")
    make_user(email="op-cl2@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    headers = auth_headers("op-cl2@kijapa.com", PASSWORD)

    response = client.post(
        _start_url(), json={"template_id": template.id, "shift": "NOITE"}, headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_only_active_template_items_are_precreated(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Ativo")
    make_checklist_template_item(template=template, description="Inativo", active=False)
    headers = auth_headers("gestor-cl3@kijapa.com", PASSWORD)

    response = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)

    descriptions = {item["item_description_snapshot"] for item in response.json()["items"]}
    assert descriptions == {"Ativo"}


def test_snapshot_is_frozen_even_if_template_item_is_edited_later(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    item = make_checklist_template_item(template=template, description="Texto original")
    headers = auth_headers("gestor-cl4@kijapa.com", PASSWORD)

    start_response = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)
    execution_id = start_response.json()["id"]

    edit_response = client.patch(
        f"/api/v1/checklist-template-items/{item.id}", json={"description": "Texto editado depois"}, headers=headers
    )
    assert edit_response.status_code == status.HTTP_200_OK

    get_response = client.get(f"{CHECKLISTS_URL}/{execution_id}", headers=headers)
    assert get_response.json()["items"][0]["item_description_snapshot"] == "Texto original"


def test_cannot_start_second_execution_same_template_shift_store_today(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-cl5@kijapa.com", PASSWORD)

    first = client.post(_start_url(), json={"template_id": template.id, "shift": "TARDE"}, headers=headers)
    assert first.status_code == status.HTTP_201_CREATED

    second = client.post(_start_url(), json={"template_id": template.id, "shift": "TARDE"}, headers=headers)
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["code"] == "CHECKLIST_ALREADY_IN_PROGRESS"


def test_different_shift_is_not_blocked_as_duplicate(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-cl6@kijapa.com", PASSWORD)

    first = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)
    second = client.post(_start_url(), json={"template_id": template.id, "shift": "TARDE"}, headers=headers)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED


def test_stale_in_progress_from_a_previous_day_does_not_block_a_new_one(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_template_item,
    make_checklist_execution,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl7@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    make_checklist_execution(
        template=template, shift="MANHA", status="IN_PROGRESS", executed_by_user_id=manager.id, started_at=yesterday
    )
    headers = auth_headers("gestor-cl7@kijapa.com", PASSWORD)

    response = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED


def test_cannot_start_execution_from_inactive_template(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl8@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id, active=False)
    headers = auth_headers("gestor-cl8@kijapa.com", PASSWORD)

    response = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "TEMPLATE_INACTIVE"


def test_cannot_start_execution_for_template_from_another_store(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-cl@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    template_b = make_checklist_template(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_user(email="gestor-a-cl@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers = auth_headers("gestor-a-cl@kijapa.com", PASSWORD)

    response = client.post(_start_url(), json={"template_id": template_b.id, "shift": "MANHA"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


# --- responder / concluir ----------------------------------------------------------


def test_answer_item_and_complete_execution(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl9@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Item obrigatório", required=True)
    headers = auth_headers("gestor-cl9@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    answer_response = client.patch(
        _item_url(execution["id"], item_id), json={"response": "OK", "observation": "Tudo certo."}, headers=headers
    )
    assert answer_response.status_code == status.HTTP_200_OK
    assert answer_response.json()["response"] == "OK"
    assert answer_response.json()["observation"] == "Tudo certo."

    complete_response = client.post(_complete_url(execution["id"]), headers=headers)
    assert complete_response.status_code == status.HTTP_200_OK
    body = complete_response.json()
    assert body["status"] == "COMPLETED"
    assert body["finished_at"] is not None


def test_answering_item_that_requires_photo_without_photo_is_rejected(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo1@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Foto da geladeira", requires_photo=True)
    headers = auth_headers("gestor-cl-photo1@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]
    assert execution["items"][0]["requires_photo"] is True

    response = client.patch(_item_url(execution["id"], item_id), json={"response": "OK"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "PHOTO_PROOF_REQUIRED"


def test_answering_item_that_requires_photo_with_photo_url_succeeds(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Foto da geladeira", requires_photo=True)
    headers = auth_headers("gestor-cl-photo2@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    response = client.patch(
        _item_url(execution["id"], item_id),
        json={"response": "OK", "photo_url": "http://localhost:8000/static/uploads/foo.jpg"},
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["photo_url"] == "http://localhost:8000/static/uploads/foo.jpg"


def test_item_without_requires_photo_answers_normally_without_photo(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo3@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, requires_photo=False)
    headers = auth_headers("gestor-cl-photo3@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    response = client.patch(_item_url(execution["id"], item_id), json={"response": "OK"}, headers=headers)

    assert response.status_code == status.HTTP_200_OK


def test_upload_item_photo_returns_url_then_answer_stores_it(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo4@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, requires_photo=True)
    headers = auth_headers("gestor-cl-photo4@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    upload_response = client.post(
        f"{CHECKLISTS_URL}/{execution['id']}/items/{item_id}/photo",
        files={"photo": ("foto.jpg", b"conteudo-fake-de-imagem", "image/jpeg")},
        headers=headers,
    )
    assert upload_response.status_code == status.HTTP_200_OK
    photo_url = upload_response.json()["photo_url"]
    assert photo_url.endswith(".jpg")

    answer_response = client.patch(
        _item_url(execution["id"], item_id), json={"response": "OK", "photo_url": photo_url}, headers=headers
    )
    assert answer_response.status_code == status.HTTP_200_OK
    assert answer_response.json()["photo_url"] == photo_url


def test_answering_with_multiple_photos_stores_the_extras(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo6@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, requires_photo=True)
    headers = auth_headers("gestor-cl-photo6@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    photo_urls = []
    for filename in ("foto1.jpg", "foto2.jpg"):
        upload_response = client.post(
            f"{CHECKLISTS_URL}/{execution['id']}/items/{item_id}/photo",
            files={"photo": (filename, b"conteudo-fake-de-imagem", "image/jpeg")},
            headers=headers,
        )
        photo_urls.append(upload_response.json()["photo_url"])

    answer_response = client.patch(
        _item_url(execution["id"], item_id),
        json={"response": "OK", "photo_url": photo_urls[0], "extra_photo_urls": photo_urls[1:]},
        headers=headers,
    )
    assert answer_response.status_code == status.HTTP_200_OK
    assert answer_response.json()["photo_url"] == photo_urls[0]
    assert answer_response.json()["extra_photo_urls"] == photo_urls[1:]


def test_upload_item_photo_rejects_non_image(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl-photo5@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, requires_photo=True)
    headers = auth_headers("gestor-cl-photo5@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    item_id = execution["items"][0]["id"]

    response = client.post(
        f"{CHECKLISTS_URL}/{execution['id']}/items/{item_id}/photo",
        files={"photo": ("arquivo.txt", b"nao e uma imagem", "text/plain")},
        headers=headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "INVALID_PHOTO"


def test_cannot_complete_with_required_item_unanswered(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl10@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Obrigatório", required=True)
    headers = auth_headers("gestor-cl10@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()

    response = client.post(_complete_url(execution["id"]), headers=headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    body = response.json()
    assert body["code"] == "CHECKLIST_INCOMPLETE"
    assert body["missing_item_ids"] == [execution["items"][0]["id"]]


def test_non_required_item_can_stay_blank(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl11@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Obrigatório", required=True)
    make_checklist_template_item(template=template, description="Opcional", required=False)
    headers = auth_headers("gestor-cl11@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    required_item = next(item for item in execution["items"] if item["item_description_snapshot"] == "Obrigatório")
    client.patch(_item_url(execution["id"], required_item["id"]), json={"response": "OK"}, headers=headers)

    response = client.post(_complete_url(execution["id"]), headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "COMPLETED"


def test_cannot_answer_item_after_execution_completed(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl12@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, required=False)
    headers = auth_headers("gestor-cl12@kijapa.com", PASSWORD)

    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    client.post(_complete_url(execution["id"]), headers=headers)

    response = client.patch(
        _item_url(execution["id"], execution["items"][0]["id"]), json={"response": "OK"}, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "CHECKLIST_NOT_IN_PROGRESS"


# --- validação cruzada --------------------------------------------------------------


def _start_and_complete(client, headers, template_id, shift="MANHA", response_value="OK"):
    execution = client.post(_start_url(), json={"template_id": template_id, "shift": shift}, headers=headers).json()
    item_id = execution["items"][0]["id"]
    client.patch(_item_url(execution["id"], item_id), json={"response": response_value}, headers=headers)
    complete = client.post(_complete_url(execution["id"]), headers=headers).json()
    return complete, item_id


def test_lider_validates_item_as_aprovado(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl13@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Desligar a fritadeira")
    gestor_headers = auth_headers("gestor-cl13@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, gestor_headers, template.id)

    lider = make_user(email="lider-cl13@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    lider_headers = auth_headers("lider-cl13@kijapa.com", PASSWORD)

    response = client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=lider_headers)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["result"] == "APROVADO"
    assert body["validated_by_user_id"] == lider.id
    assert body["original_response_snapshot"] == {
        "item_description": "Desligar a fritadeira",
        "response": "OK",
        "observation": None,
    }


def test_cannot_validate_own_checklist(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl13b@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Desligar a fritadeira")
    headers = auth_headers("gestor-cl13b@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, headers, template.id)

    response = client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["code"] == "SAME_USER_VALIDATION_FORBIDDEN"


def test_divergente_requires_justification(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl14@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-cl14@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, headers, template.id)

    make_user(email="lider-cl14@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    validator_headers = auth_headers("lider-cl14@kijapa.com", PASSWORD)

    without_justification = client.post(
        _validate_url(execution["id"], item_id), json={"result": "DIVERGENTE"}, headers=validator_headers
    )
    assert without_justification.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    with_justification = client.post(
        _validate_url(execution["id"], item_id),
        json={"result": "DIVERGENTE", "justification": "Fritadeira encontrada ligada."},
        headers=validator_headers,
    )
    assert with_justification.status_code == status.HTTP_201_CREATED
    assert with_justification.json()["result"] == "DIVERGENTE"
    assert with_justification.json()["justification"] == "Fritadeira encontrada ligada."


def test_operacional_cannot_validate(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl15@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    gestor_headers = auth_headers("gestor-cl15@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, gestor_headers, template.id)

    make_user(email="op-cl15@kijapa.com", password=PASSWORD, role="OPERACIONAL", store_id=store.id)
    op_headers = auth_headers("op-cl15@kijapa.com", PASSWORD)

    response = client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=op_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_cannot_validate_same_item_twice(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl16@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-cl16@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, headers, template.id)

    make_user(email="lider-cl16@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    validator_headers = auth_headers("lider-cl16@kijapa.com", PASSWORD)

    first = client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=validator_headers)
    second = client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=validator_headers)

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_409_CONFLICT
    assert second.json()["code"] == "CHECKLIST_ITEM_ALREADY_VALIDATED"


def test_cannot_validate_before_execution_completed(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl17@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template)
    headers = auth_headers("gestor-cl17@kijapa.com", PASSWORD)
    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()

    response = client.post(
        _validate_url(execution["id"], execution["items"][0]["id"]), json={"result": "APROVADO"}, headers=headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["code"] == "CHECKLIST_NOT_COMPLETED"


def test_cannot_validate_unanswered_item(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl18@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, description="Obrigatório", required=True)
    make_checklist_template_item(template=template, description="Opcional", required=False)
    headers = auth_headers("gestor-cl18@kijapa.com", PASSWORD)
    execution = client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers).json()
    required_item = next(item for item in execution["items"] if item["item_description_snapshot"] == "Obrigatório")
    optional_item = next(item for item in execution["items"] if item["item_description_snapshot"] == "Opcional")
    client.patch(_item_url(execution["id"], required_item["id"]), json={"response": "OK"}, headers=headers)
    client.post(_complete_url(execution["id"]), headers=headers)

    response = client.post(_validate_url(execution["id"], optional_item["id"]), json={"result": "APROVADO"}, headers=headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "ITEM_NOT_ANSWERED"


def test_fully_validated_flag(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl19@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, required=True)
    headers = auth_headers("gestor-cl19@kijapa.com", PASSWORD)
    execution, item_id = _start_and_complete(client, headers, template.id)

    make_user(email="lider-cl19@kijapa.com", password=PASSWORD, role="LIDER", store_id=store.id)
    validator_headers = auth_headers("lider-cl19@kijapa.com", PASSWORD)

    before = client.get(f"{CHECKLISTS_URL}/{execution['id']}", headers=headers)
    assert before.json()["fully_validated"] is False

    client.post(_validate_url(execution["id"], item_id), json={"result": "APROVADO"}, headers=validator_headers)

    after = client.get(f"{CHECKLISTS_URL}/{execution['id']}", headers=headers)
    assert after.json()["fully_validated"] is True


def test_tenant_isolation_on_execution(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store_a = make_store(name="Loja A")
    store_b = make_store(name="Loja B")
    manager_b = make_user(email="gestor-b-cl2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_b.id)
    template_b = make_checklist_template(store_id=store_b.id, created_by_user_id=manager_b.id)
    make_checklist_template_item(template=template_b)
    headers_b = auth_headers("gestor-b-cl2@kijapa.com", PASSWORD)
    execution = client.post(_start_url(), json={"template_id": template_b.id, "shift": "MANHA"}, headers=headers_b).json()

    make_user(email="gestor-a-cl2@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store_a.id)
    headers_a = auth_headers("gestor-a-cl2@kijapa.com", PASSWORD)

    response = client.get(f"{CHECKLISTS_URL}/{execution['id']}", headers=headers_a)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_executions_filters_by_status_and_shift(
    client: TestClient, make_user, auth_headers, make_store, make_checklist_template, make_checklist_template_item
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl20@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    make_checklist_template_item(template=template, required=False)
    headers = auth_headers("gestor-cl20@kijapa.com", PASSWORD)
    client.post(_start_url(), json={"template_id": template.id, "shift": "MANHA"}, headers=headers)
    client.post(_start_url(), json={"template_id": template.id, "shift": "TARDE"}, headers=headers)

    response = client.get(f"{CHECKLISTS_URL}?shift=MANHA&status=IN_PROGRESS", headers=headers)

    executions = response.json()
    assert len(executions) == 1
    assert executions[0]["shift"] == "MANHA"


def test_list_executions_filters_by_date_range(
    client: TestClient,
    make_user,
    auth_headers,
    make_store,
    make_checklist_template,
    make_checklist_execution,
) -> None:
    store = make_store()
    manager = make_user(email="gestor-cl21@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    template = make_checklist_template(store_id=store.id, created_by_user_id=manager.id)
    today = datetime.now(timezone.utc)
    make_checklist_execution(
        template=template, status="COMPLETED", executed_by_user_id=manager.id, started_at=today - timedelta(days=10)
    )
    make_checklist_execution(
        template=template, status="COMPLETED", executed_by_user_id=manager.id, started_at=today - timedelta(days=3)
    )
    make_checklist_execution(template=template, status="IN_PROGRESS", executed_by_user_id=manager.id, started_at=today)
    headers = auth_headers("gestor-cl21@kijapa.com", PASSWORD)

    started_from = (today - timedelta(days=7)).date().isoformat()
    response = client.get(f"{CHECKLISTS_URL}?started_from={started_from}", headers=headers)

    executions = response.json()
    assert len(executions) == 2

    started_to = (today - timedelta(days=5)).date().isoformat()
    older_only = client.get(f"{CHECKLISTS_URL}?started_to={started_to}", headers=headers)
    assert len(older_only.json()) == 1


def test_get_unknown_execution_returns_404(client: TestClient, make_user, auth_headers, make_store) -> None:
    store = make_store()
    make_user(email="gestor-cl404@kijapa.com", password=PASSWORD, role="GESTOR", store_id=store.id)
    headers = auth_headers("gestor-cl404@kijapa.com", PASSWORD)

    response = client.get(f"{CHECKLISTS_URL}/999999", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
