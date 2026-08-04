from datetime import datetime, timedelta, timezone

from tests.conftest import login


def _create_order(client):
    headers = login(client)
    analysis = client.post(
        "/api/v1/safety/analyze",
        headers=headers,
        files={"image": ("site.jpg", b"demo", "image/jpeg")},
        data={
            "project_id": "PRJ-001",
            "location": "B1",
            "work_type": "主体结构",
            "demo_scenario": "no_helmet",
        },
    ).json()["data"]
    order = client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={"task_id": analysis["task_id"], "confirm_ai_draft": True},
    ).json()["data"]
    return headers, order


def test_work_order_detail_contains_source_image_and_evidence(client):
    headers, order = _create_order(client)

    response = client.get(f"/api/v1/work-orders/{order['id']}", headers=headers)

    assert response.status_code == 200
    detail = response.json()["data"]
    assert detail["file_url"].startswith("/storage/uploads/")
    assert detail["annotated_url"].startswith("/storage/annotated/")
    assert detail["evidence"]


def test_work_order_attachment_is_persisted_and_linked_to_event(client, db_session):
    headers, order = _create_order(client)

    response = client.post(
        f"/api/v1/work-orders/{order['id']}/attachments",
        headers=headers,
        files={"attachment": ("fix.jpg", b"fixed", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["stored"] is True
    assert data["upload_id"]
    assert data["file_url"].startswith("/storage/uploads/")

    from app.core.config import settings
    from app.models import Upload, WorkOrderEvent

    upload = db_session.query(Upload).filter_by(id=data["upload_id"]).one()
    assert (settings.upload_dir / upload.stored_name).exists()
    assert db_session.query(WorkOrderEvent).filter_by(attachment_upload_id=data["upload_id"]).count() == 1


def test_closing_work_order_requires_review_note(client):
    headers, order = _create_order(client)
    client.patch(
        f"/api/v1/work-orders/{order['id']}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    client.patch(
        f"/api/v1/work-orders/{order['id']}/status",
        headers=headers,
        json={"status": "pending_review"},
    )

    response = client.patch(
        f"/api/v1/work-orders/{order['id']}/status",
        headers=headers,
        json={"status": "closed"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "WORK_ORDER_REVIEW_NOTE_REQUIRED"


def test_work_order_list_filters_by_assignee_and_deadline(client):
    headers, order = _create_order(client)
    deadline = datetime.fromisoformat(order["deadline"].replace("Z", "+00:00"))
    response = client.get(
        "/api/v1/work-orders",
        headers=headers,
        params={
            "assignee_user_id": order["assignee_user_id"],
            "deadline_from": (deadline - timedelta(minutes=1)).astimezone(timezone.utc).isoformat(),
            "deadline_to": (deadline + timedelta(minutes=1)).astimezone(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [order["id"]]

    other_assignee = client.get("/api/v1/work-orders", headers=headers, params={"assignee_user_id": "USR-004"})
    assert other_assignee.status_code == 200
    assert other_assignee.json()["data"] == []
