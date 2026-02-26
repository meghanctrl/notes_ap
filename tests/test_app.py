from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import app as flask_app
from app import get_db, init_db


@pytest.fixture()
def app(tmp_path: Path):
    db_path = tmp_path / "test.db"
    flask_app.config.update(TESTING=True, DATABASE=str(db_path))

    with flask_app.app_context():
        init_db()

    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def insert_note(
    app,
    *,
    title: str = "Test note",
    content: str = "Body",
    category: str = "general",
    status: str = "todo",
    priority: str = "medium",
    due_date: str | None = None,
    is_pinned: int = 0,
    is_archived: int = 0,
    is_deleted: int = 0,
) -> int:
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO notes
                (title, content, category, status, priority, due_date, is_pinned, is_archived, is_deleted)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                content,
                category,
                status,
                priority,
                due_date,
                is_pinned,
                is_archived,
                is_deleted,
            ),
        )
        db.commit()
        return cursor.lastrowid


def test_index_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No notes found for this view." in response.data


def test_create_note_with_metadata_success(client):
    response = client.post(
        "/notes",
        data={
            "title": "Deploy checklist",
            "content": "Ship release candidate",
            "category": "work",
            "status": "in_progress",
            "priority": "high",
            "due_date": "2026-03-05",
            "is_pinned": "on",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Deploy checklist" in response.data
    assert b"In Progress" in response.data
    assert b"High" in response.data
    assert b"Pinned" in response.data


def test_create_note_validation_errors(client):
    response = client.post("/notes", data={"title": "   ", "status": "todo", "priority": "low"})
    assert response.status_code == 400
    assert b"Title is required." in response.data

    response = client.post(
        "/notes",
        data={
            "title": "Bad date",
            "status": "todo",
            "priority": "low",
            "due_date": "2026-22-99",
        },
    )
    assert response.status_code == 400
    assert b"Due date must be a valid date" in response.data


def test_search_and_filters(client, app):
    insert_note(app, title="Alpha roadmap", category="work", status="done", priority="high")
    insert_note(app, title="Weekend shopping", category="personal", status="todo", priority="low")

    response = client.get("/?q=Alpha")
    assert b"Alpha roadmap" in response.data
    assert b"Weekend shopping" not in response.data

    response = client.get("/?status=done")
    assert b"Alpha roadmap" in response.data
    assert b"Weekend shopping" not in response.data

    response = client.get("/?category=personal")
    assert b"Weekend shopping" in response.data
    assert b"Alpha roadmap" not in response.data


def test_pin_toggle(client, app):
    note_id = insert_note(app, title="Pin me")

    response = client.post(f"/notes/{note_id}/pin", data={"next": "/"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Pinned" in response.data

    response = client.post(f"/notes/{note_id}/pin", data={"next": "/"}, follow_redirects=True)
    assert response.status_code == 200


def test_archive_view_and_unarchive(client, app):
    note_id = insert_note(app, title="Archive target")

    response = client.post(
        f"/notes/{note_id}/archive",
        data={"next": "/?view=archived"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Archive target" in response.data

    active_response = client.get("/?view=active")
    assert b"Archive target" not in active_response.data

    response = client.post(
        f"/notes/{note_id}/archive",
        data={"next": "/?view=active"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Archive target" in response.data


def test_trash_restore_and_purge(client, app):
    note_id = insert_note(app, title="Trash target")

    response = client.post(
        f"/notes/{note_id}/trash",
        data={"next": "/?view=trash"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Trash target" in response.data

    response = client.post(
        f"/notes/{note_id}/restore",
        data={"next": "/?view=active"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Trash target" in response.data

    client.post(f"/notes/{note_id}/trash", data={"next": "/?view=trash"}, follow_redirects=True)
    response = client.post(
        f"/notes/{note_id}/purge",
        data={"next": "/?view=trash"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Trash target" not in response.data


def test_edit_note_with_metadata(client, app):
    note_id = insert_note(app, title="Old", status="todo", priority="low")

    response = client.post(
        f"/notes/{note_id}/edit",
        data={
            "title": "Updated",
            "content": "Better details",
            "category": "project",
            "status": "done",
            "priority": "high",
            "due_date": "2026-04-01",
            "is_pinned": "on",
            "next": "/",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Updated" in response.data
    assert b"Done" in response.data
    assert b"High" in response.data


def test_api_endpoints(client, app):
    note_id = insert_note(app, title="API note", category="backend", status="done")

    response = client.get("/api/notes?view=active&status=done")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["filters"]["status"] == "done"
    assert any(note["title"] == "API note" for note in payload["notes"])

    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    detail = response.get_json()
    assert detail["title"] == "API note"


def test_init_db_migrates_legacy_schema(tmp_path: Path):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

    flask_app.config.update(TESTING=True, DATABASE=str(db_path))
    with flask_app.app_context():
        init_db()
        columns = {
            row["name"]
            for row in get_db().execute("PRAGMA table_info(notes)").fetchall()
        }

    assert "category" in columns
    assert "status" in columns
    assert "priority" in columns
    assert "is_deleted" in columns


def test_non_existent_note_actions_return_404(client):
    response = client.post("/notes/99999/pin", data={"next": "/"})
    assert response.status_code == 404

    response = client.post("/notes/99999/archive", data={"next": "/"})
    assert response.status_code == 404

    response = client.post("/notes/99999/trash", data={"next": "/"})
    assert response.status_code == 404

    response = client.post("/notes/99999/purge", data={"next": "/"})
    assert response.status_code == 404
