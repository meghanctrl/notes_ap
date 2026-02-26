# Simple End-to-End Guide (Flask + API + SQLite)

This file explains the app in very simple language.

## 1. What this app is

This is a **Notes app**.

You can:
- Create a note
- See all notes
- Edit a note
- Delete a note

This is called **CRUD**:
- **C**reate
- **R**ead
- **U**pdate
- **D**elete

## 2. Very simple idea of the stack

- **Flask**: The Python web framework. It runs the server and handles URLs.
- **HTML templates**: The pages the user sees in the browser.
- **SQLite**: A small file database (`notes.db`) that stores notes.
- **API routes**: URL paths in Flask that receive requests and do work.

Think of it like this:
- Browser asks Flask for something.
- Flask talks to SQLite if needed.
- Flask sends HTML back to browser.

## 3. Main files and what they do

- `app.py`
  - Starts Flask app
  - Creates DB table if needed
  - Contains all routes (`/`, `/notes`, edit, delete)
- `templates/index.html`
  - Home page with create form + notes list
- `templates/edit.html`
  - Edit form page
- `templates/404.html`
  - "Not found" page
- `static/styles.css`
  - Basic styling
- `notes.db`
  - SQLite file where data is stored

## 4. Step-by-step: app startup

1. You run: `uv run flask --app app run --debug`
2. Flask starts.
3. `app.py` runs `init_db()`.
4. `init_db()` creates `notes` table if it does not exist.
5. Server waits for browser requests.

## 5. Step-by-step: opening the home page

1. Browser opens `http://127.0.0.1:5000/`
2. Flask route `GET /` runs.
3. Flask reads all notes from SQLite.
4. Flask renders `templates/index.html` with those notes.
5. Browser shows the page.

## 6. Step-by-step: creating a note (Create)

1. User fills title/content form and clicks **Create**.
2. Browser sends `POST /notes`.
3. Flask route `create_note()` gets form data.
4. Flask checks title is not empty.
5. If title is valid:
   - Flask inserts row into SQLite `notes` table.
   - Flask redirects back to `/`.
6. Browser loads `/` again and now shows new note.

If title is empty:
- Flask returns same page with error: "Title is required."

## 7. Step-by-step: reading notes (Read)

1. Every time `/` is opened, Flask runs a SQL `SELECT`.
2. It gets all notes from SQLite.
3. It passes notes to template.
4. Template loops through notes and displays them.

## 8. Step-by-step: editing a note (Update)

1. User clicks **Edit** on a note.
2. Browser opens `GET /notes/<id>/edit`.
3. Flask finds that note by ID.
4. Flask renders `edit.html` with note values.
5. User changes text and clicks **Save**.
6. Browser sends `POST /notes/<id>/edit`.
7. Flask validates title and runs SQL `UPDATE`.
8. Flask redirects to `/` so user sees updated note.

If ID is not found:
- Flask returns 404 page.

## 9. Step-by-step: deleting a note (Delete)

1. User clicks **Delete**.
2. Browser sends `POST /notes/<id>/delete`.
3. Flask runs SQL `DELETE` for that ID.
4. Flask redirects to `/`.
5. Browser shows list without that note.

If ID is not found:
- Flask returns 404 page.

## 10. What "API" means in this app

An API route is just a URL your code listens to.

In this app, these are the important routes:
- `GET /` -> show notes page
- `POST /notes` -> create note
- `GET /notes/<id>/edit` -> show edit page
- `POST /notes/<id>/edit` -> save changes
- `POST /notes/<id>/delete` -> delete note

So yes, this app has APIs, but they are used by HTML forms (server-rendered style), not by frontend JavaScript.

## 11. How data moves end to end (one-line summary)

**Browser form -> Flask route -> SQLite query -> Flask template/redirect -> Browser updates page**

## 12. How to run locally

1. `uv venv`
2. `uv sync`
3. `uv run flask --app app run --debug`
4. Open `http://127.0.0.1:5000`

## 13. How to run tests

Run:

`uv run pytest`

Tests check:
- Home page works
- Create works
- Validation works
- Edit works
- Delete works
- 404 behavior works
