# Line-by-Line Explanation (Inline Code Snippets)

This document explains the upgraded app in beginner-friendly language with code snippets inline.

---

## File: `app.py`

### 1) Imports and constants

```python
from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for

STATUSES = ("todo", "in_progress", "done")
PRIORITIES = ("low", "medium", "high")
VIEWS = ("active", "archived", "trash")
```

What this does:
- Imports Flask tools for HTML routes and JSON API routes.
- Defines allowed values for status, priority, and list views.

### 2) App config

```python
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-key"),
    DATABASE=os.environ.get("NOTES_DB_PATH", str(DEFAULT_DB_PATH)),
)
```

What this does:
- Creates Flask app.
- Sets DB path and secret key (from env vars if available).

### 3) DB connection per request

```python
def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db
```

What this does:
- Opens SQLite connection once per request.
- `row_factory` lets us use `row["column"]` style.

### 4) DB cleanup

```python
@app.teardown_appcontext
def close_db(_: object | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
```

What this does:
- Closes DB connection automatically at the end of request.

### 5) Schema creation + migration

```python
def ensure_notes_schema(db: sqlite3.Connection) -> None:
    db.execute("""
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
    """)
```

What this does:
- Creates full notes table with advanced metadata.

```python
existing_columns = {row["name"] for row in db.execute("PRAGMA table_info(notes)").fetchall()}
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
```

What this does:
- Migrates old DBs automatically by adding missing columns.

### 6) Input validation helpers

```python
def normalize_note_form(form: Any) -> tuple[dict[str, Any], str | None]:
    title = form.get("title", "").strip()
    ...
    if not title:
        return {}, "Title is required."
    if status not in STATUSES:
        return {}, "Status is invalid."
    if priority not in PRIORITIES:
        return {}, "Priority is invalid."
```

What this does:
- Validates form input before writing to DB.
- Enforces allowed values.

### 7) Filter parsing and SQL where clause

```python
def load_filters(args: Any) -> dict[str, str]:
    filters = {
        "q": args.get("q", "").strip(),
        "status": args.get("status", "all").strip(),
        "priority": args.get("priority", "all").strip(),
        "category": args.get("category", "all").strip() or "all",
        "view": args.get("view", "active").strip(),
    }
```

What this does:
- Reads filter query parameters from URL.

```python
def build_where_clause(filters: dict[str, str]) -> tuple[str, list[Any]]:
    if filters["view"] == "trash":
        clauses.append("is_deleted = 1")
    elif filters["view"] == "archived":
        clauses.extend(["is_deleted = 0", "is_archived = 1"])
    else:
        clauses.extend(["is_deleted = 0", "is_archived = 0"])
```

What this does:
- Turns UI tab selection into SQL filtering rules.

### 8) Main list query

```python
SELECT ...
FROM notes
WHERE {where_clause}
ORDER BY
    is_pinned DESC,
    CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
    CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END,
    due_date ASC,
    updated_at DESC,
    id DESC
```

What this does:
- Shows pinned notes first.
- Then high priority first.
- Then earlier due dates.
- Then latest updates.

### 9) Route: dashboard

```python
@app.route("/")
def index():
    return render_index()
```

What this does:
- Renders dashboard with filters, notes, and counts.

### 10) Route: create

```python
@app.post("/notes")
def create_note():
    note_data, error = normalize_note_form(request.form)
    if error:
        return render_index(error=error, form_data=request.form.to_dict(), status_code=400)
    ... INSERT INTO notes ...
```

What this does:
- Validates user input.
- Inserts note if valid.
- Returns form error if invalid.

### 11) Route: edit page + update

```python
@app.route("/notes/<int:note_id>/edit")
def edit_note(note_id: int):
    note = get_note_or_404(note_id)
    if note["is_deleted"]:
        abort(404)
```

```python
@app.post("/notes/<int:note_id>/edit")
def update_note(note_id: int):
    ...
    UPDATE notes SET title=?, content=?, category=?, status=?, priority=?, due_date=?, is_pinned=?, updated_at=CURRENT_TIMESTAMP
```

What this does:
- Opens edit page for existing non-deleted note.
- Saves full metadata changes.

### 12) Action routes

```python
@app.post("/notes/<int:note_id>/pin")
@app.post("/notes/<int:note_id>/archive")
@app.post("/notes/<int:note_id>/trash")
@app.post("/notes/<int:note_id>/restore")
@app.post("/notes/<int:note_id>/purge")
```

What this does:
- Pin/unpin
- Archive/unarchive
- Move to trash
- Restore from trash
- Delete forever

### 13) JSON API routes

```python
@app.get("/api/notes")
def list_notes_api():
    filters = load_filters(request.args)
    notes = [serialize_note(note) for note in fetch_notes(filters)]
    return jsonify({"filters": filters, "counts": fetch_counts(), "notes": notes})

@app.get("/api/notes/<int:note_id>")
def note_detail_api(note_id: int):
    return jsonify(serialize_note(get_note_or_404(note_id)))
```

What this does:
- Provides JSON endpoints for integrations/frontends.

---

## File: `templates/index.html`

### Create form snippet

```html
<form method="post" action="{{ url_for('create_note') }}" class="create-form">
  <input id="create-title" name="title" ...>
  <textarea id="create-content" name="content"></textarea>
  <input id="create-category" name="category" ...>
  <select id="create-status" name="status">...</select>
  <select id="create-priority" name="priority">...</select>
  <input id="create-due-date" name="due_date" type="date">
  <input id="create-pinned" name="is_pinned" type="checkbox">
  <button id="create-submit" type="submit">Create Note</button>
</form>
```

What this does:
- Collects all advanced fields for a new note.

### View tabs + filters snippet

```html
<a id="tab-active" ...>Active ({{ counts['active'] }})</a>
<a id="tab-archived" ...>Archived ({{ counts['archived'] }})</a>
<a id="tab-trash" ...>Trash ({{ counts['trash'] }})</a>

<form method="get" action="{{ url_for('index') }}" class="filter-form">
  <input type="hidden" name="view" value="{{ filters['view'] }}">
  <input id="search-q" name="q" ...>
  <select id="filter-status" name="status">...</select>
  <select id="filter-priority" name="priority">...</select>
  <select id="filter-category" name="category">...</select>
</form>
```

What this does:
- Lets user switch views and apply filters.

### Note action snippet

```html
<form method="post" action="{{ url_for('toggle_pin', note_id=note['id']) }}">...</form>
<form method="post" action="{{ url_for('toggle_archive', note_id=note['id']) }}">...</form>
<form method="post" action="{{ url_for('move_to_trash', note_id=note['id']) }}">...</form>
```

What this does:
- Gives quick actions on each note.

---

## File: `templates/edit.html`

```html
<form method="post" action="{{ url_for('update_note', note_id=note['id']) }}" class="create-form">
  <input type="hidden" name="next" value="{{ next_url }}">
  <input id="title" name="title" ...>
  <textarea id="content" name="content"></textarea>
  <input id="category" name="category" ...>
  <select id="status" name="status">...</select>
  <select id="priority" name="priority">...</select>
  <input id="due_date" name="due_date" type="date" ...>
  <input id="is_pinned" name="is_pinned" type="checkbox" ...>
</form>
```

What this does:
- Lets user edit all metadata and return to previous filtered page.

---

## File: `static/styles.css`

Key styling areas:

```css
.tab.active { background: #dcfce7; }
.note-card { border: 1px solid var(--border); }
.badge.status.done { background: #dcfce7; }
.badge.priority.high { background: #fee2e2; }
```

What this does:
- Makes tabs, note cards, and badges visually distinct.
- Uses responsive layout for mobile screens.

---

## File: `tests/test_app.py`

### Create test

```python
def test_create_note_with_metadata_success(client):
    response = client.post("/notes", data={...}, follow_redirects=True)
    assert b"Deploy checklist" in response.data
```

### Filters test

```python
def test_search_and_filters(client, app):
    insert_note(app, title="Alpha roadmap", ...)
    response = client.get("/?q=Alpha")
    assert b"Alpha roadmap" in response.data
```

### Archive/trash tests

```python
def test_archive_view_and_unarchive(...)
def test_trash_restore_and_purge(...)
```

### API test

```python
def test_api_endpoints(client, app):
    response = client.get("/api/notes?view=active&status=done")
    payload = response.get_json()
```

### Migration test

```python
def test_init_db_migrates_legacy_schema(tmp_path):
    ...
    init_db()
    columns = {row["name"] for row in get_db().execute("PRAGMA table_info(notes)").fetchall()}
    assert "category" in columns
```

What these tests guarantee:
- Core CRUD + advanced features work.
- API works.
- Old DB schema is auto-upgraded.

---

## File: `demo/record_demo.py`

This script automates the browser flow and records a 1-minute video with captions.

High-level flow in code:

```python
# 1) open app
# 2) create multiple notes with metadata
# 3) search and filter
# 4) pin, archive, unarchive
# 5) move to trash, restore, purge
# 6) save video as demo/videos/crud-demo.webm
```

---

## End-to-end summary

```text
Browser action -> Flask route -> validation -> SQLite write/read -> HTML/JSON response -> browser updates
```

The app is now a practical note dashboard, not only basic CRUD.
