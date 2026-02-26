# Simple End-to-End Guide (Advanced Notes App)

This explains the app in very simple language.

## 1. What this app does

This is a **notes dashboard**.

You can:
- Create a note
- Read notes
- Edit notes
- Move notes to archive
- Move notes to trash
- Restore from trash
- Delete forever
- Search and filter notes
- Pin important notes on top

So it is still CRUD, but with more real-world features.

## 2. Tech in simple words

- **Flask**: the Python web app server
- **SQLite**: a single file database (`notes.db`)
- **Templates**: HTML pages shown in browser
- **Routes**: URL paths that run Python code

## 3. Main files

- `app.py`: backend routes, DB logic, schema migration, API endpoints
- `templates/index.html`: main dashboard with forms, filters, and note actions
- `templates/edit.html`: edit page
- `templates/404.html`: not found page
- `static/styles.css`: app styling
- `tests/test_app.py`: automated tests
- `demo/record_demo.py`: creates the 1-minute captioned demo video

## 4. App startup flow

1. You run: `uv run flask --app app run --debug`
2. Flask starts.
3. `init_db()` runs.
4. It creates table if missing.
5. It also adds new columns if the DB is old (migration).
6. Server starts listening for browser requests.

## 5. Create note flow

1. User fills create form.
2. Browser sends `POST /notes`.
3. Flask validates input:
   - title required
   - status/priority allowed values
   - due date valid format
4. Flask inserts note into SQLite.
5. Flask redirects to `/`.
6. Updated list is shown.

## 6. Read/search/filter flow

1. Browser opens `/`.
2. Flask reads query params (`q`, `status`, `priority`, `category`, `view`).
3. Flask builds SQL conditions.
4. Flask fetches matching notes.
5. Flask sends data to `index.html`.
6. Browser shows filtered result list.

## 7. Edit flow

1. User clicks Edit.
2. Browser opens `GET /notes/<id>/edit`.
3. Flask loads note.
4. User updates fields and submits.
5. Browser sends `POST /notes/<id>/edit`.
6. Flask validates and updates row.
7. Redirect back to list.

## 8. Extra action flows

### Pin/unpin
- Route: `POST /notes/<id>/pin`
- Toggles pinned state.

### Archive/unarchive
- Route: `POST /notes/<id>/archive`
- Toggles archived state.

### Move to trash
- Route: `POST /notes/<id>/trash`
- Marks note as deleted (soft delete).

### Restore from trash
- Route: `POST /notes/<id>/restore`
- Moves note back to active view.

### Delete forever
- Route: `POST /notes/<id>/purge`
- Permanently removes row from DB.

## 9. Views (tabs)

- **Active**: normal working notes
- **Archived**: notes kept for reference
- **Trash**: soft-deleted notes

Each tab has its own count at the top.

## 10. API routes

- `GET /api/notes` returns JSON list (supports filters)
- `GET /api/notes/<id>` returns one note in JSON

This is useful if later you build a separate frontend app.

## 11. Data flow summary

**Browser -> Flask route -> Validation -> SQLite query -> Template/JSON response -> Browser**

## 12. Run locally

1. `uv venv`
2. `uv sync --dev`
3. `uv run flask --app app run --debug`
4. Open `http://127.0.0.1:5000`

## 13. Run tests

```bash
uv run pytest
```

Tests cover:
- Create/read/update
- Validation
- Search/filter
- Pin/archive/trash/restore/purge
- API responses
- Legacy schema migration

## 14. Generate 1-minute captioned demo

```bash
uv run --with playwright playwright install chromium
uv run --with playwright python demo/record_demo.py
```

Video output:

- `demo/videos/crud-demo.webm`
