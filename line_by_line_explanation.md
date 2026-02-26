# Line-by-Line Explanation (Beginner Friendly)

This guide explains the app code in simple language.

Important note:
- I explain by **line numbers** and small groups of lines.
- Grouping related lines makes it easier to understand than explaining one isolated line at a time.

---

## File: `app.py`

### Imports and app setup

- **Line 1**: `from __future__ import annotations`
  - Helps Python handle type hints more smoothly.
  - Safe to use; you can think of it as "better type hint behavior."

- **Lines 3-5**: import `os`, `sqlite3`, and `Path`.
  - `os`: read environment variables.
  - `sqlite3`: connect to SQLite database.
  - `Path`: build file paths safely.

- **Line 7**: import Flask tools:
  - `Flask`: create app.
  - `abort`: return errors like 404.
  - `g`: request-level storage (used for DB connection).
  - `redirect`, `url_for`: redirect user to another page.
  - `render_template`: render HTML templates.
  - `request`: read form data sent by browser.

- **Lines 9-10**:
  - `BASE_DIR` = folder where `app.py` lives.
  - `DEFAULT_DB_PATH` = `<project>/notes.db`.

- **Line 12**: create Flask app object.

- **Lines 13-16**: app configuration:
  - `SECRET_KEY`: used by Flask for secure features.
  - `DATABASE`: DB file path.
  - If env vars are not set, it uses defaults (`dev-secret-key` and `notes.db`).

### Database connection helpers

- **Line 19**: define `get_db()`.
  - This function gives you a DB connection.

- **Line 20**: if no DB connection is stored in `g`, create one.

- **Line 21**: connect to SQLite file path from config.

- **Line 22**: row factory gives dictionary-like rows (`row["title"]`) instead of only tuple indexes.

- **Line 23**: return the DB connection.

- **Line 26**: `@app.teardown_appcontext`
  - This means Flask runs `close_db()` automatically at end of each request.

- **Lines 27-30**:
  - Get DB from `g`.
  - If it exists, close it.
  - This prevents connection leaks.

### Database table creation

- **Line 33**: define `init_db()`.

- **Line 34**: get DB connection.

- **Lines 35-45**: run SQL to create table if it does not exist:
  - `id`: unique integer ID, auto-increment.
  - `title`: required text.
  - `content`: optional text, default empty string.
  - `created_at`: auto timestamp when inserted.
  - `updated_at`: auto timestamp (and manually updated on edit).

- **Line 46**: commit SQL changes.

### Helper for 404 on missing note

- **Line 49**: define `get_note_or_404(note_id)`.

- **Lines 50-53**:
  - Query notes table for one row with that ID.
  - `fetchone()` returns one row or `None`.

- **Lines 54-55**: if not found, immediately return HTTP 404.

- **Line 56**: return found note row.

### Route: list notes (Read)

- **Line 59**: route decorator for URL `/` (GET by default).

- **Line 60**: `index()` route function.

- **Lines 61-63**:
  - Select all notes.
  - Order newest first (`ORDER BY id DESC`).

- **Line 64**:
  - Render `index.html`.
  - Send:
    - `notes` list.
    - `error=None`.
    - empty `form_data`.

### Route: create note (Create)

- **Line 67**: route handles `POST /notes`.

- **Line 68**: `create_note()` starts.

- **Lines 69-70**:
  - Read `title` and `content` from submitted form.
  - `.strip()` removes extra spaces from start/end.

- **Line 72**: validation check: title cannot be empty after stripping.

- **Lines 73-75**:
  - Re-query notes list so page can still show notes.

- **Lines 76-84**:
  - Return `index.html` with error message.
  - Keep user-entered values in `form_data`.
  - Return status code `400` (bad request).

- **Line 86**: get DB connection.

- **Line 87**: insert new row into notes table.

- **Line 88**: commit insert.

- **Line 89**: redirect user to home page (`/`) so they can see updated list.

### Route: show edit page

- **Line 92**: route handles `GET /notes/<id>/edit`.
  - `<int:note_id>` means Flask parses integer from URL.

- **Lines 93-94**: load note or 404.

- **Line 95**: render `edit.html` with note data and no error.

### Route: save edited note (Update)

- **Line 98**: route handles `POST /notes/<id>/edit`.

- **Lines 100-101**: read and trim form fields.

- **Lines 103-105**:
  - Validate non-empty title.
  - If invalid, render same edit page with error and status `400`.

- **Line 107**: get DB connection.

- **Lines 108-115**:
  - SQL `UPDATE` note row by ID.
  - Also set `updated_at = CURRENT_TIMESTAMP`.

- **Line 116**: commit update.

- **Lines 117-118**:
  - If no rows were updated, ID did not exist.
  - Return 404.

- **Line 119**: redirect to home page.

### Route: delete note (Delete)

- **Line 122**: route handles `POST /notes/<id>/delete`.

- **Line 124**: get DB connection.

- **Line 125**: run SQL `DELETE` for that ID.

- **Line 126**: commit delete.

- **Lines 127-128**:
  - If nothing deleted, note did not exist.
  - Return 404.

- **Line 129**: redirect to home page.

### Error handler and startup

- **Line 132**: register custom handler for 404 errors.

- **Lines 133-134**:
  - Render `404.html`.
  - Return status `404`.

- **Lines 137-138**:
  - Create app context and run `init_db()` at startup.
  - Ensures table exists before requests.

- **Lines 141-142**:
  - If file run directly (`python app.py`), start Flask dev server.

---

## File: `templates/base.html`

- **Line 1**: HTML5 doctype.
- **Line 2**: `<html lang="en">`.
- **Lines 3-8**:
  - page head metadata.
  - title block (`{% block title %}`) lets child templates change title.
  - includes CSS from `/static/styles.css`.
- **Lines 9-14**:
  - common page layout.
  - heading with home link.
  - `{% block content %}` placeholder where each page injects its own body.

This is called a **base template** (layout shared by all pages).

---

## File: `templates/index.html`

- **Line 1**: extends `base.html`.
- **Line 3**: sets page title block to "All Notes".
- **Line 5**: starts content block.

### Create form section

- **Lines 6-7**: section/card and heading "Create Note".
- **Lines 8-10**: if error exists, show it in red.
- **Line 11**: form sends POST to `create_note` route (`/notes`).
- **Lines 12-19**:
  - title label + input.
  - input value is repopulated from `form_data` when validation fails.
  - `required` asks browser to enforce non-empty title too.
- **Lines 21-22**:
  - content label + textarea.
  - also repopulated from `form_data`.
- **Line 24**: submit button.
- **Line 25**: form ends.
- **Line 26**: section ends.

### Notes list section

- **Lines 28-29**: section/card and heading "Notes".
- **Line 30**: if notes exist.
- **Line 31**: start list.
- **Line 32**: loop through notes.
- **Lines 33-35**: show title and content.
- **Lines 36-41**: action area:
  - edit link to `/notes/<id>/edit`.
  - delete form posts to `/notes/<id>/delete`.
- **Lines 42-44**: finish one note and loop.
- **Line 45**: else case if notes list is empty.
- **Line 46**: show "No notes yet."
- **Lines 47-49**: close condition, section, and content block.

---

## File: `templates/edit.html`

- **Line 1**: extends base template.
- **Line 3**: page title "Edit Note".
- **Line 5**: start content block.
- **Lines 6-7**: card + heading.
- **Lines 8-10**: show error if validation failed.
- **Line 11**: form posts to update route for this specific note ID.
- **Lines 12-13**: title field prefilled with current note title.
- **Lines 15-16**: content textarea prefilled with current note content.
- **Line 18**: save button.
- **Line 19**: cancel link back to home page.
- **Lines 20-22**: close form/card/block.

---

## File: `templates/404.html`

- **Line 1**: extends base template.
- **Line 3**: page title "Not Found".
- **Line 5**: start content block.
- **Lines 6-9**:
  - show 404 message.
  - link back to home page.
- **Lines 10-11**: close section and block.

---

## File: `static/styles.css`

This file only controls how things look.

- **Lines 1-3**: `box-sizing` reset for easier layout sizing.
- **Lines 5-10**: body styles (font, background, text color, no default margin).
- **Lines 12-16**: center main container and set max width.
- **Lines 18-24**: heading spacing.
- **Lines 26-29**: home link style.
- **Lines 31-37**: card look (white background, border, rounded corners).
- **Lines 39-43**: form label formatting.
- **Lines 45-53**: shared style for input and textarea.
- **Lines 55-62**: button style (green background, white text).
- **Lines 64-66**: link color.
- **Lines 68-70**: cancel link spacing.
- **Lines 72-76**: remove default list styles for notes.
- **Lines 78-86**: spacing + border between note items.
- **Lines 88-95**: title/content spacing + preserve content line breaks.
- **Lines 97-105**: align edit and delete actions in a row.
- **Lines 107-110**: error text styling (red and bold).

---

## File: `tests/test_app.py`

This file tests the app behavior automatically.

### Imports

- **Line 1**: future annotations helper.
- **Line 3**: `Path` for file paths.
- **Line 5**: import `pytest`.
- **Lines 7-8**: import Flask app and DB helper functions from `app.py`.

### Fixtures (test setup)

- **Lines 11-20**: `app` fixture.
  - Creates temporary DB path (`tmp_path/test.db`).
  - Updates Flask config to use test DB and testing mode.
  - Initializes DB table.
  - Yields app to tests.

- **Lines 22-24**: `client` fixture.
  - Creates Flask test client so tests can send fake HTTP requests.

### Helper for creating data

- **Lines 27-34**: `insert_note(...)`.
  - Inserts one note directly into test DB.
  - Returns inserted note ID.
  - Used in edit/delete tests.

### Actual tests

- **Lines 37-40**: `test_index_empty_state`
  - `GET /` should return 200 and show "No notes yet."

- **Lines 43-52**: `test_create_note_success`
  - Posts valid note.
  - Follows redirect.
  - Confirms note text appears in response.

- **Lines 54-57**: `test_create_note_validation_error`
  - Posts blank title.
  - Expects HTTP 400 and validation message.

- **Lines 60-64**: `test_edit_note_page`
  - Inserts note, opens edit page, expects 200 and original text.

- **Lines 67-77**: `test_update_note_success`
  - Inserts note, posts updates, follows redirect.
  - Confirms new text present and old text absent.

- **Lines 80-84**: `test_delete_note_success`
  - Inserts note, deletes it, follows redirect.
  - Confirms deleted text is gone.

- **Lines 87-95**: `test_non_existent_note_returns_404`
  - For missing IDs:
    - GET edit page should be 404.
    - POST update should be 404.
    - POST delete should be 404.

---

## File: `pyproject.toml`

- **Line 1**: start project metadata section.
- **Lines 2-6**: project name/version/description/readme/Python version.
- **Lines 7-9**: app dependencies.
  - Flask is required for app runtime.
- **Lines 11-14**: dev dependency group.
  - Pytest is required for tests.
- **Lines 16-17**: pytest config.
  - Adds current project root to Python path for imports like `from app import ...`.

---

## How everything works together (simple flow)

1. Start server with `uv run flask --app app run --debug`.
2. Flask starts and ensures DB table exists.
3. Browser opens `/`.
4. Flask reads notes from SQLite and renders HTML.
5. User submits form (create/edit/delete).
6. Flask route receives request, runs SQL query, commits changes.
7. Flask redirects back to `/`.
8. Browser shows updated list.

That is the full end-to-end cycle.
