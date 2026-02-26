# Line-by-Line Explanation (With Inline Code Snippets)

This is a beginner-friendly explanation of the full codebase.

How to read this:
- I explain by line numbers.
- I include small code snippets inline, then explain them in simple words.
- Some lines are explained in groups when they work together.

---

## 1. `app.py` (Main backend file)

### Lines 1-7: imports

```python
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, url_for
```

What this means:
- `os`: read environment variables.
- `sqlite3`: connect to SQLite database.
- `Path`: create safe file paths.
- Flask imports:
  - `Flask`: creates the app
  - `request`: gets form data from browser
  - `render_template`: sends HTML pages
  - `redirect` + `url_for`: move user to another URL
  - `abort`: return errors like 404
  - `g`: temporary storage for one request (used for DB connection)

### Lines 9-16: paths and config

```python
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "notes.db"

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-key"),
    DATABASE=os.environ.get("NOTES_DB_PATH", str(DEFAULT_DB_PATH)),
)
```

What this means:
- `BASE_DIR`: folder where `app.py` exists.
- `DEFAULT_DB_PATH`: default DB file is `notes.db` in project root.
- `SECRET_KEY` and `DATABASE` can come from environment variables.
- If env vars are missing, it uses defaults.

### Lines 19-23: open/reuse DB connection

```python
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db
```

What this means:
- During one request, create one DB connection and store in `g`.
- Reuse that same connection in the same request.
- `sqlite3.Row` lets you access columns by name, like `row["title"]`.

### Lines 26-30: close DB after request

```python
@app.teardown_appcontext
def close_db(_: object | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
```

What this means:
- Flask automatically calls this after each request.
- It safely closes DB connection if it was opened.

### Lines 33-46: create table if not exists

```python
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
```

What this means:
- `init_db()` creates the `notes` table if it is missing.
- Table columns:
  - `id`: unique row ID
  - `title`: required
  - `content`: optional
  - timestamps for created/updated time

### Lines 49-56: helper to fetch one note or return 404

```python
def get_note_or_404(note_id: int) -> sqlite3.Row:
    note = get_db().execute(
        "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?",
        (note_id,),
    ).fetchone()
    if note is None:
        abort(404)
    return note
```

What this means:
- Find one note by ID.
- If not found, stop immediately with 404 page.

### Lines 59-64: home page route (Read)

```python
@app.route("/")
def index() -> str:
    notes = get_db().execute(
        "SELECT id, title, content, created_at, updated_at FROM notes ORDER BY id DESC"
    ).fetchall()
    return render_template("index.html", notes=notes, error=None, form_data={})
```

What this means:
- URL `/` loads all notes (newest first).
- Flask passes data to `index.html`.

### Lines 67-89: create note route (Create)

```python
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
```

What this means:
- Reads form values from browser.
- If title is empty, return form page with error.
- If valid, insert into DB and redirect back to `/`.

### Lines 92-95: open edit page

```python
@app.route("/notes/<int:note_id>/edit")
def edit_note(note_id: int) -> str:
    note = get_note_or_404(note_id)
    return render_template("edit.html", note=note, error=None)
```

What this means:
- URL like `/notes/5/edit` opens edit page for note `5`.
- If note does not exist, user gets 404.

### Lines 98-119: save edited note (Update)

```python
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
```

What this means:
- Reads new form values.
- Validates title.
- Runs SQL `UPDATE`.
- If ID not found (`rowcount == 0`), returns 404.
- Redirects to home page.

### Lines 122-129: delete note (Delete)

```python
@app.post("/notes/<int:note_id>/delete")
def delete_note(note_id: int):
    db = get_db()
    result = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()
    if result.rowcount == 0:
        abort(404)
    return redirect(url_for("index"))
```

What this means:
- Deletes note by ID.
- If ID not found, returns 404.
- On success, redirects to `/`.

### Lines 132-142: custom 404 page + startup

```python
@app.errorhandler(404)
def not_found(_: Exception):
    return render_template("404.html"), 404


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
```

What this means:
- Any 404 error shows `404.html`.
- On startup, app makes sure DB/table exist.
- If file runs directly, start dev server.

---

## 2. `templates/base.html` (shared layout)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}Notes CRUD{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
  </head>
  <body>
    <main class="container">
      <h1><a class="home-link" href="{{ url_for('index') }}">Notes CRUD</a></h1>
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

What this means:
- This is the shared page shell for all pages.
- Child templates fill:
  - `title` block
  - `content` block

---

## 3. `templates/index.html` (home page with Create + list)

### Top of file and create form

```html
{% extends "base.html" %}
{% block title %}All Notes{% endblock %}
{% block content %}
  <section class="card">
    <h2>Create Note</h2>
    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}
    <form method="post" action="{{ url_for('create_note') }}">
      <label for="title">Title</label>
      <input id="title" name="title" type="text" value="{{ form_data.get('title', '') }}" required>
      <label for="content">Content</label>
      <textarea id="content" name="content" rows="4">{{ form_data.get('content', '') }}</textarea>
      <button type="submit">Create</button>
    </form>
  </section>
```

What this means:
- Shows create form.
- If backend sends `error`, it displays it.
- `form_data` refills fields after validation failure.

### Notes list and actions

```html
  <section class="card">
    <h2>Notes</h2>
    {% if notes %}
      <ul class="notes">
        {% for note in notes %}
          <li>
            <h3>{{ note["title"] }}</h3>
            <p>{{ note["content"] }}</p>
            <div class="actions">
              <a href="{{ url_for('edit_note', note_id=note['id']) }}">Edit</a>
              <form method="post" action="{{ url_for('delete_note', note_id=note['id']) }}">
                <button type="submit">Delete</button>
              </form>
            </div>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p>No notes yet.</p>
    {% endif %}
  </section>
{% endblock %}
```

What this means:
- Loops through notes and shows each one.
- Edit uses link (`GET`).
- Delete uses form (`POST`) for safer data-changing action.

---

## 4. `templates/edit.html` (edit page)

```html
{% extends "base.html" %}
{% block title %}Edit Note{% endblock %}
{% block content %}
  <section class="card">
    <h2>Edit Note</h2>
    {% if error %}
      <p class="error">{{ error }}</p>
    {% endif %}
    <form method="post" action="{{ url_for('update_note', note_id=note['id']) }}">
      <label for="title">Title</label>
      <input id="title" name="title" type="text" value="{{ note['title'] }}" required>
      <label for="content">Content</label>
      <textarea id="content" name="content" rows="4">{{ note['content'] }}</textarea>
      <button type="submit">Save</button>
      <a class="secondary-link" href="{{ url_for('index') }}">Cancel</a>
    </form>
  </section>
{% endblock %}
```

What this means:
- Prefills form with existing note data.
- Submit goes to update route.
- Cancel returns to home page.

---

## 5. `templates/404.html` (not found page)

```html
{% extends "base.html" %}
{% block title %}Not Found{% endblock %}
{% block content %}
  <section class="card">
    <h2>404 - Not Found</h2>
    <p>The requested note does not exist.</p>
    <a href="{{ url_for('index') }}">Back to all notes</a>
  </section>
{% endblock %}
```

What this means:
- Friendly page shown when note ID does not exist.

---

## 6. `static/styles.css` (styling)

### Basic page + card styles

```css
body {
  margin: 0;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  background: #f4f4f4;
  color: #222;
}

.container {
  max-width: 760px;
  margin: 2rem auto;
  padding: 0 1rem 2rem;
}

.card {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}
```

What this means:
- Sets clean font/colors.
- Centers content.
- Makes each section look like a card.

### Form and action styles

```css
input,
textarea {
  width: 100%;
  margin-bottom: 0.8rem;
  padding: 0.5rem;
  border: 1px solid #bbb;
  border-radius: 6px;
}

button {
  border: none;
  background: #0f766e;
  color: #fff;
  padding: 0.45rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
}

.actions {
  display: flex;
  gap: 0.8rem;
  align-items: center;
}
```

What this means:
- Inputs fill available width.
- Button has green theme.
- Edit/Delete controls are aligned in one row.

---

## 7. `tests/test_app.py` (automated checks)

### Imports and fixtures

```python
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
```

What this means:
- Tests run on a temporary DB, not your real `notes.db`.
- `client` sends fake HTTP requests (no browser needed).

### Helper: create a note directly in test DB

```python
def insert_note(app, title: str = "Test note", content: str = "Body") -> int:
    with app.app_context():
        db = get_db()
        cursor = db.execute(
            "INSERT INTO notes (title, content) VALUES (?, ?)", (title, content)
        )
        db.commit()
        return cursor.lastrowid
```

What this means:
- Quickly creates test data for edit/delete tests.

### Example tests

```python
def test_create_note_success(client):
    response = client.post(
        "/notes",
        data={"title": "First", "content": "Hello"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"First" in response.data
```

What this means:
- Tests create flow end to end.
- Checks that response contains created text.

```python
def test_non_existent_note_returns_404(client):
    response = client.get("/notes/99999/edit")
    assert response.status_code == 404
```

What this means:
- Tests error handling for invalid IDs.

---

## 8. `pyproject.toml` (dependencies and tool config)

```toml
[project]
name = "simple-flask-crud"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=3.1.0,<4.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0,<9.0.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
```

What this means:
- Runtime dependency: Flask.
- Dev dependency: Pytest.
- `pythonpath = ["."]` allows tests to import `app.py` cleanly.

---

## 9. End-to-end request flow (simple)

Code path for creating a note:

```text
Browser form -> POST /notes -> create_note() -> INSERT into SQLite -> redirect("/") -> index() -> render index.html
```

Code path for editing:

```text
GET /notes/<id>/edit -> edit.html form -> POST /notes/<id>/edit -> UPDATE SQLite -> redirect("/")
```

Code path for deleting:

```text
POST /notes/<id>/delete -> DELETE SQLite -> redirect("/")
```

That is the full app behavior in beginner terms, with code snippets inline.
