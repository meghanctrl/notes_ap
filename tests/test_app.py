from __future__ import annotations

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


def insert_note(app, title: str = "Test note", content: str = "Body") -> int:
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)", (title, content)
        )
        db.commit()
        return cursor.lastrowid


def test_index_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No notes yet." in response.data


def test_create_note_success(client):
    response = client.post(
        "/notes",
        data={"title": "First", "content": "Hello"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"First" in response.data
    assert b"Hello" in response.data


def test_create_note_validation_error(client):
    response = client.post("/notes", data={"title": "   ", "content": "Hello"})
    assert response.status_code == 400
    assert b"Title is required." in response.data


def test_edit_note_page(client, app):
    note_id = insert_note(app, title="Original", content="Original content")
    response = client.get(f"/notes/{note_id}/edit")
    assert response.status_code == 200
    assert b"Original" in response.data


def test_update_note_success(client, app):
    note_id = insert_note(app, title="Old", content="Text")
    response = client.post(
        f"/notes/{note_id}/edit",
        data={"title": "New", "content": "Updated"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"New" in response.data
    assert b"Updated" in response.data
    assert b"Old" not in response.data


def test_delete_note_success(client, app):
    note_id = insert_note(app, title="Delete me", content="Soon gone")
    response = client.post(f"/notes/{note_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Delete me" not in response.data


def test_non_existent_note_returns_404(client):
    response = client.get("/notes/99999/edit")
    assert response.status_code == 404

    response = client.post("/notes/99999/edit", data={"title": "X", "content": ""})
    assert response.status_code == 404

    response = client.post("/notes/99999/delete")
    assert response.status_code == 404
