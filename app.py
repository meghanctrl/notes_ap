from __future__ import annotations

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "notes.db"
STATUSES = ("todo", "in_progress", "done")
PRIORITIES = ("low", "medium", "high")
VIEWS = ("active", "archived", "trash")

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


def ensure_notes_schema(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            category TEXT NOT NULL DEFAULT 'general',
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'medium',
            due_date TEXT,
            is_pinned INTEGER NOT NULL DEFAULT 0,
            is_archived INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    existing_columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(notes)").fetchall()
        if row["name"]
    }
    additions = {
        "category": "category TEXT NOT NULL DEFAULT 'general'",
        "status": "status TEXT NOT NULL DEFAULT 'todo'",
        "priority": "priority TEXT NOT NULL DEFAULT 'medium'",
        "due_date": "due_date TEXT",
        "is_pinned": "is_pinned INTEGER NOT NULL DEFAULT 0",
        "is_archived": "is_archived INTEGER NOT NULL DEFAULT 0",
        "is_deleted": "is_deleted INTEGER NOT NULL DEFAULT 0",
    }

    for name, definition in additions.items():
        if name not in existing_columns:
            db.execute(f"ALTER TABLE notes ADD COLUMN {definition}")

    db.execute(
        """
        UPDATE notes
        SET
            category = COALESCE(NULLIF(TRIM(category), ''), 'general'),
            status = CASE
                WHEN status IN ('todo', 'in_progress', 'done') THEN status
                ELSE 'todo'
            END,
            priority = CASE
                WHEN priority IN ('low', 'medium', 'high') THEN priority
                ELSE 'medium'
            END,
            is_pinned = CASE WHEN is_pinned IS NULL THEN 0 ELSE is_pinned END,
            is_archived = CASE WHEN is_archived IS NULL THEN 0 ELSE is_archived END,
            is_deleted = CASE WHEN is_deleted IS NULL THEN 0 ELSE is_deleted END
        """
    )

    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_notes_state ON notes(is_deleted, is_archived, is_pinned)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_status ON notes(status, priority)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category)")


def init_db() -> None:
    db = get_db()
    ensure_notes_schema(db)
    db.commit()


def format_label(value: str) -> str:
    return value.replace("_", " ").title()


@app.context_processor
def inject_helpers() -> dict[str, Any]:
    return {
        "format_status": format_label,
        "format_priority": format_label,
    }


def sanitize_next_url(next_url: str | None, fallback: str) -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return fallback


def redirect_to_next(default_endpoint: str = "index"):
    fallback = url_for(default_endpoint)
    target = sanitize_next_url(request.form.get("next"), fallback)
    return redirect(target)


def parse_due_date(raw_due_date: str) -> tuple[str | None, str | None]:
    if not raw_due_date:
        return None, None
    try:
        parsed = date.fromisoformat(raw_due_date)
    except ValueError:
        return None, "Due date must be a valid date in YYYY-MM-DD format."
    return parsed.isoformat(), None


def normalize_note_form(form: Any) -> tuple[dict[str, Any], str | None]:
    title = form.get("title", "").strip()
    content = form.get("content", "").strip()
    category = form.get("category", "general").strip() or "general"
    status = form.get("status", "todo").strip()
    priority = form.get("priority", "medium").strip()
    due_date_raw = form.get("due_date", "").strip()
    is_pinned = 1 if form.get("is_pinned") in {"on", "1", "true"} else 0

    if not title:
        return {}, "Title is required."
    if status not in STATUSES:
        return {}, "Status is invalid."
    if priority not in PRIORITIES:
        return {}, "Priority is invalid."

    due_date, due_error = parse_due_date(due_date_raw)
    if due_error:
        return {}, due_error

    return {
        "title": title,
        "content": content,
        "category": category,
        "status": status,
        "priority": priority,
        "due_date": due_date,
        "is_pinned": is_pinned,
    }, None


def default_form_data() -> dict[str, Any]:
    return {
        "title": "",
        "content": "",
        "category": "general",
        "status": "todo",
        "priority": "medium",
        "due_date": "",
        "is_pinned": 0,
    }


def load_filters(args: Any) -> dict[str, str]:
    filters = {
        "q": args.get("q", "").strip(),
        "status": args.get("status", "all").strip(),
        "priority": args.get("priority", "all").strip(),
        "category": args.get("category", "all").strip() or "all",
        "view": args.get("view", "active").strip(),
    }

    if filters["status"] not in {"all", *STATUSES}:
        filters["status"] = "all"
    if filters["priority"] not in {"all", *PRIORITIES}:
        filters["priority"] = "all"
    if filters["view"] not in VIEWS:
        filters["view"] = "active"

    return filters


def build_where_clause(filters: dict[str, str]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if filters["view"] == "trash":
        clauses.append("is_deleted = 1")
    elif filters["view"] == "archived":
        clauses.extend(["is_deleted = 0", "is_archived = 1"])
    else:
        clauses.extend(["is_deleted = 0", "is_archived = 0"])

    if filters["q"]:
        clauses.append("(title LIKE ? OR content LIKE ? OR category LIKE ?)")
        wildcard = f"%{filters['q']}%"
        params.extend([wildcard, wildcard, wildcard])

    if filters["status"] != "all":
        clauses.append("status = ?")
        params.append(filters["status"])

    if filters["priority"] != "all":
        clauses.append("priority = ?")
        params.append(filters["priority"])

    if filters["category"] != "all":
        clauses.append("category = ?")
        params.append(filters["category"])

    return " AND ".join(clauses), params


def fetch_notes(filters: dict[str, str]) -> list[sqlite3.Row]:
    where_clause, params = build_where_clause(filters)
    db = get_db()
    return db.execute(
        f"""
        SELECT
            id,
            title,
            content,
            category,
            status,
            priority,
            due_date,
            is_pinned,
            is_archived,
            is_deleted,
            created_at,
            updated_at
        FROM notes
        WHERE {where_clause}
        ORDER BY
            is_pinned DESC,
            CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END,
            due_date ASC,
            updated_at DESC,
            id DESC
        """,
        params,
    ).fetchall()


def fetch_counts() -> dict[str, int]:
    row = get_db().execute(
        """
        SELECT
            SUM(CASE WHEN is_deleted = 0 AND is_archived = 0 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN is_deleted = 0 AND is_archived = 1 THEN 1 ELSE 0 END) AS archived,
            SUM(CASE WHEN is_deleted = 1 THEN 1 ELSE 0 END) AS trash
        FROM notes
        """
    ).fetchone()

    return {
        "active": int(row["active"] or 0),
        "archived": int(row["archived"] or 0),
        "trash": int(row["trash"] or 0),
    }


def fetch_categories() -> list[str]:
    rows = get_db().execute(
        """
        SELECT DISTINCT category
        FROM notes
        WHERE category IS NOT NULL AND TRIM(category) != ''
        ORDER BY category COLLATE NOCASE ASC
        """
    ).fetchall()
    return [row["category"] for row in rows]


def current_url() -> str:
    full_path = request.full_path
    if full_path.endswith("?"):
        return full_path[:-1]
    return full_path


def render_index(
    *,
    error: str | None = None,
    form_data: dict[str, Any] | None = None,
    status_code: int = 200,
):
    filters = load_filters(request.args)
    notes = fetch_notes(filters)
    counts = fetch_counts()
    categories = fetch_categories()

    create_form = default_form_data()
    if form_data:
        create_form.update(form_data)

    return (
        render_template(
            "index.html",
            notes=notes,
            filters=filters,
            counts=counts,
            categories=categories,
            statuses=STATUSES,
            priorities=PRIORITIES,
            error=error,
            form_data=create_form,
            current_url=current_url(),
        ),
        status_code,
    )


def get_note_or_404(note_id: int) -> sqlite3.Row:
    note = get_db().execute(
        """
        SELECT
            id,
            title,
            content,
            category,
            status,
            priority,
            due_date,
            is_pinned,
            is_archived,
            is_deleted,
            created_at,
            updated_at
        FROM notes
        WHERE id = ?
        """,
        (note_id,),
    ).fetchone()

    if note is None:
        abort(404)
    return note


@app.route("/")
def index():
    return render_index()


@app.post("/notes")
def create_note():
    note_data, error = normalize_note_form(request.form)
    if error:
        return render_index(error=error, form_data=request.form.to_dict(), status_code=400)

    db = get_db()
    db.execute(
        """
        INSERT INTO notes (title, content, category, status, priority, due_date, is_pinned)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            note_data["title"],
            note_data["content"],
            note_data["category"],
            note_data["status"],
            note_data["priority"],
            note_data["due_date"],
            note_data["is_pinned"],
        ),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/notes/<int:note_id>/edit")
def edit_note(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)

    next_url = sanitize_next_url(request.args.get("next"), url_for("index"))
    return render_template(
        "edit.html",
        note=note,
        error=None,
        next_url=next_url,
        statuses=STATUSES,
        priorities=PRIORITIES,
    )


@app.post("/notes/<int:note_id>/edit")
def update_note(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)

    note_data, error = normalize_note_form(request.form)
    next_url = sanitize_next_url(request.form.get("next"), url_for("index"))

    if error:
        form_note = dict(note)
        form_note.update(request.form.to_dict())
        form_note["is_pinned"] = 1 if request.form.get("is_pinned") else 0
        return (
            render_template(
                "edit.html",
                note=form_note,
                error=error,
                next_url=next_url,
                statuses=STATUSES,
                priorities=PRIORITIES,
            ),
            400,
        )

    db = get_db()
    result = db.execute(
        """
        UPDATE notes
        SET
            title = ?,
            content = ?,
            category = ?,
            status = ?,
            priority = ?,
            due_date = ?,
            is_pinned = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            note_data["title"],
            note_data["content"],
            note_data["category"],
            note_data["status"],
            note_data["priority"],
            note_data["due_date"],
            note_data["is_pinned"],
            note_id,
        ),
    )
    db.commit()

    if result.rowcount == 0:
        abort(404)
    return redirect(next_url)


@app.post("/notes/<int:note_id>/pin")
def toggle_pin(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)

    db = get_db()
    db.execute(
        "UPDATE notes SET is_pinned = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (0 if note["is_pinned"] else 1, note_id),
    )
    db.commit()
    return redirect_to_next()


@app.post("/notes/<int:note_id>/archive")
def toggle_archive(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)

    db = get_db()
    new_archive_state = 0 if note["is_archived"] else 1
    db.execute(
        """
        UPDATE notes
        SET is_archived = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_archive_state, note_id),
    )
    db.commit()
    return redirect_to_next()


@app.post("/notes/<int:note_id>/trash")
def move_to_trash(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)

    db = get_db()
    db.execute(
        """
        UPDATE notes
        SET
            is_deleted = 1,
            is_archived = 0,
            is_pinned = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (note_id,),
    )
    db.commit()
    return redirect_to_next()


@app.post("/notes/<int:note_id>/restore")
def restore_note(note_id: int):
    note = get_note_or_404(note_id)
    if not note["is_deleted"]:
        return redirect_to_next()

    db = get_db()
    db.execute(
        """
        UPDATE notes
        SET
            is_deleted = 0,
            is_archived = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (note_id,),
    )
    db.commit()
    return redirect_to_next()


@app.post("/notes/<int:note_id>/purge")
def purge_note(note_id: int):
    _ = get_note_or_404(note_id)
    db = get_db()
    result = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    if result.rowcount == 0:
        abort(404)
    return redirect_to_next()


def serialize_note(note: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": note["id"],
        "title": note["title"],
        "content": note["content"],
        "category": note["category"],
        "status": note["status"],
        "priority": note["priority"],
        "due_date": note["due_date"],
        "is_pinned": bool(note["is_pinned"]),
        "is_archived": bool(note["is_archived"]),
        "is_deleted": bool(note["is_deleted"]),
        "created_at": note["created_at"],
        "updated_at": note["updated_at"],
    }


@app.get("/api/notes")
def list_notes_api():
    filters = load_filters(request.args)
    notes = [serialize_note(note) for note in fetch_notes(filters)]
    return jsonify(
        {
            "filters": filters,
            "counts": fetch_counts(),
            "notes": notes,
        }
    )


@app.get("/api/notes/<int:note_id>")
def note_detail_api(note_id: int):
    return jsonify(serialize_note(get_note_or_404(note_id)))


@app.errorhandler(404)
def not_found(_: Exception):
    return render_template("404.html"), 404


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
