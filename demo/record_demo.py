from __future__ import annotations

import shutil
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://127.0.0.1:5000"
VIDEO_DIR = Path("demo/videos")
VIDEO_DIR.mkdir(parents=True, exist_ok=True)


def ensure_caption_overlay(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const existing = document.getElementById('demo-caption-overlay');
          if (existing) return;

          const wrap = document.createElement('div');
          wrap.id = 'demo-caption-overlay';
          wrap.style.position = 'fixed';
          wrap.style.left = '50%';
          wrap.style.bottom = '20px';
          wrap.style.transform = 'translateX(-50%)';
          wrap.style.maxWidth = '80%';
          wrap.style.padding = '10px 14px';
          wrap.style.background = 'rgba(15, 23, 42, 0.84)';
          wrap.style.color = '#f8fafc';
          wrap.style.fontFamily = 'Arial, sans-serif';
          wrap.style.fontSize = '18px';
          wrap.style.lineHeight = '1.35';
          wrap.style.borderRadius = '10px';
          wrap.style.zIndex = '999999';
          wrap.style.boxShadow = '0 8px 28px rgba(0,0,0,0.35)';
          wrap.textContent = 'Demo starting...';
          document.body.appendChild(wrap);
        }
        """
    )


def set_caption(page: Page, text: str, hold_ms: int) -> None:
    ensure_caption_overlay(page)
    page.evaluate(
        """
        (captionText) => {
          const el = document.getElementById('demo-caption-overlay');
          if (el) el.textContent = captionText;
        }
        """,
        text,
    )
    page.wait_for_timeout(hold_ms)


def create_note(
    page: Page,
    *,
    title: str,
    content: str,
    category: str,
    status: str,
    priority: str,
    due_date: str,
    pinned: bool,
) -> None:
    page.fill("#create-title", title)
    page.fill("#create-content", content)
    page.fill("#create-category", category)
    page.select_option("#create-status", status)
    page.select_option("#create-priority", priority)
    page.fill("#create-due-date", due_date)

    if pinned:
        if not page.is_checked("#create-pinned"):
            page.check("#create-pinned")
    else:
        if page.is_checked("#create-pinned"):
            page.uncheck("#create-pinned")

    page.click("#create-submit")
    page.wait_for_load_state("networkidle")


def note_card(page: Page, title: str):
    return page.locator(".note-card", has_text=title).first


def main() -> int:
    seed = int(time.time())
    note_a = f"Release Plan {seed}"
    note_b = f"UI Polish {seed}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=220)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)

        set_caption(page, "Welcome to Notes Command Center: an advanced Flask + SQLite CRUD app.", 5000)

        set_caption(page, "Feature 1: Create notes with metadata like category, status, priority, due date, and pinning.", 2800)
        create_note(
            page,
            title=note_a,
            content="Plan the upcoming release with clear backend milestones.",
            category="engineering",
            status="in_progress",
            priority="high",
            due_date="2026-03-20",
            pinned=True,
        )
        set_caption(page, "First note created as HIGH priority and pinned.", 3000)

        create_note(
            page,
            title=note_b,
            content="Refresh card spacing and improve mobile layout consistency.",
            category="design",
            status="todo",
            priority="medium",
            due_date="2026-03-28",
            pinned=False,
        )
        set_caption(page, "Second note created with a different category and status.", 3000)

        set_caption(page, "Feature 2: Full-text search across title, content, and category.", 2200)
        page.fill("#search-q", "Release")
        page.click("#filter-apply")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Search narrowed the list to matching notes.", 3000)

        set_caption(page, "Feature 3: Filter by status, priority, and category.", 2200)
        page.select_option("#filter-status", "in_progress")
        page.select_option("#filter-priority", "high")
        page.select_option("#filter-category", "engineering")
        page.click("#filter-apply")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Filters now show only engineering notes in progress with high priority.", 3200)

        page.click("#filter-clear")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Filters cleared back to the full active list.", 2500)

        set_caption(page, "Feature 4: Quick actions on each note card.", 2000)
        note_card(page, note_b).locator("button.action-pin").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Pinned the UI note so it can stay near the top.", 3000)

        note_card(page, note_b).locator("button.action-archive").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Feature 5: Archived notes move out of active view.", 3200)

        page.click("#tab-archived")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Archived tab keeps older notes organized but still accessible.", 3200)

        note_card(page, note_b).locator("button.action-archive").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Unarchived the note to bring it back into active work.", 3000)

        page.click("#tab-active")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Feature 6: Trash workflow for safe soft-delete and recovery.", 2400)

        note_card(page, note_b).locator("button.action-trash").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Moved note to trash (soft delete).", 2600)

        page.click("#tab-trash")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Trash tab shows deleted notes with restore and permanent delete options.", 3200)

        note_card(page, note_b).locator("button.action-restore").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Restored note back to active list.", 2400)

        page.click("#tab-active")
        page.wait_for_load_state("networkidle")
        note_card(page, note_b).locator("button.action-trash").click()
        page.wait_for_load_state("networkidle")

        page.click("#tab-trash")
        page.wait_for_load_state("networkidle")
        note_card(page, note_b).locator("button.action-purge").click()
        page.wait_for_load_state("networkidle")
        set_caption(page, "Then permanently deleted that note from trash.", 3000)

        page.click("#tab-active")
        page.wait_for_load_state("networkidle")
        set_caption(page, "Bonus: JSON APIs are available at /api/notes and /api/notes/<id>.", 3800)

        set_caption(page, "Demo complete: searchable, filterable, pinnable notes with archive and trash flows.", 6500)

        video = page.video
        context.close()
        browser.close()

        if video is None:
            print("Failed: no video object was generated.")
            return 1

        raw_video_path = Path(video.path())
        output_path = VIDEO_DIR / "crud-demo.webm"
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(raw_video_path), str(output_path))
        print(output_path.resolve())
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
