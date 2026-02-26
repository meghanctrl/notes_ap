# Notes Command Center (Flask + SQLite)

A richer CRUD notes app built with Flask and SQLite.

## Features

- Create notes with metadata: title, content, category, status, priority, due date, pinned flag
- Search notes by title/content/category
- Filter notes by status, priority, category
- View tabs: Active, Archived, Trash
- Pin/unpin notes
- Archive/unarchive notes
- Move notes to trash, restore from trash, permanently delete
- JSON API endpoints
- Auto schema migration for old `notes` tables

## Stack

- Flask (server + routing + templates)
- SQLite (database)
- Jinja2 templates (UI)
- Pytest (tests)
- Playwright (demo recording)

## Setup

```bash
uv venv
uv sync --dev
```

## Run

```bash
uv run flask --app app run --debug
```

Open `http://127.0.0.1:5000`.

## Test

```bash
uv run pytest
```

## API

- `GET /api/notes`
  - Supports query params: `view`, `q`, `status`, `priority`, `category`
- `GET /api/notes/<id>`

## Demo Recording

Generate a 1-minute captioned demo video:

```bash
uv run --with playwright playwright install chromium
uv run --with playwright python demo/record_demo.py
```

Output:

- `demo/videos/crud-demo.webm`
