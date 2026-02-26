from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "notes.db"

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-key"),
    DATABASE=os.environ.get("NOTES_DB_PATH", str(DEFAULT_DB_PATH)),
)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: object | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


def get_note_or_404(note_id: int) -> sqlite3.Row:
    note = get_db().execute(
        "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if note is None:
        abort(404)
    return note


@app.route("/")
def index() -> str:
    notes = get_db().execute(
        "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY id DESC"
    ).fetchall()
    return render_template("index.html", notes=notes, error=None, form_data={})


@app.post("/notes")
def create_note():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title:
        notes = get_db().execute(
            "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY id DESC"
        ).fetchall()
        return (
            render_template(
                "index.html",
                notes=notes,
                error="Title is required.",
                form_data={"title": title, "content": content},
            ),
            400,
        )

    db = get_db()
    db.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (title, content))
    db.commit()
    return redirect(url_for("index"))


@app.route("/notes/<int:note_id>/edit")
def edit_note(note_id: int) -> str:
    note = get_note_or_404(note_id)
    return render_template("edit.html", note=note, error=None)


@app.post("/notes/<int:note_id>/edit")
def update_note(note_id: int):
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title:
        note = get_note_or_404(note_id)
        return render_template("edit.html", note=note, error="Title is required."), 400

    db = get_db()
    result = db.execute(
        """
        UPDATE notes
        SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (title, content, note_id),
    )
    db.commit()
    if result.rowcount == 0:
        abort(404)
    return redirect(url_for("index"))


@app.post("/notes/<int:note_id>/delete")
def delete_note(note_id: int):
    db = get_db()
    result = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    if result.rowcount == 0:
        abort(404)
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_: Exception):
    return render_template("404.html"), 404


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
