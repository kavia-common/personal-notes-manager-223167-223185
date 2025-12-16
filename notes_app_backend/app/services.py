from __future__ import annotations

from typing import List, Optional, Tuple

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import Note


class NotesService:
    """Service handling CRUD operations for notes with DB as primary storage and in-memory fallback."""

    def __init__(self) -> None:
        self._fallback_enabled = False
        self._mem_store = {}
        self._mem_next_id = 1

    def _should_use_fallback(self) -> bool:
        return self._fallback_enabled

    def enable_fallback(self) -> None:
        self._fallback_enabled = True
        current_app.logger.warning("NotesService falling back to in-memory storage due to DB error or FS unavailability.")

    def create_note(self, title: str, content: Optional[str]) -> Note:
        if self._should_use_fallback():
            nid = self._mem_next_id
            self._mem_next_id += 1
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            data = {"id": nid, "title": title, "content": content or "", "created_at": now, "updated_at": now}
            self._mem_store[nid] = data
            # Return a simple object-like with to_dict
            class _Obj:
                def __init__(self, d): self._d = d
                def to_dict(self): return dict(self._d)
            return _Obj(data)
        try:
            note = Note(title=title, content=content or "")
            db.session.add(note)
            db.session.commit()
            return note
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception("DB error on create_note: %s", e)
            # Enable fallback on first DB failure
            self.enable_fallback()
            return self.create_note(title, content)

    def get_note(self, note_id: int) -> Optional[Note]:
        if self._should_use_fallback():
            data = self._mem_store.get(note_id)
            if not data:
                return None
            class _Obj:
                def __init__(self, d): self._d = d
                def to_dict(self): return dict(self._d)
            return _Obj(data)
        return db.session.get(Note, note_id)

    def update_note(self, note_id: int, title: Optional[str], content: Optional[str]) -> Optional[Note]:
        if self._should_use_fallback():
            data = self._mem_store.get(note_id)
            if not data:
                return None
            from datetime import datetime, timezone
            if title is not None:
                data["title"] = title
            if content is not None:
                data["content"] = content
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            class _Obj:
                def __init__(self, d): self._d = d
                def to_dict(self): return dict(self._d)
            return _Obj(data)
        try:
            note = db.session.get(Note, note_id)
            if not note:
                return None
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            db.session.commit()
            return note
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception("DB error on update_note: %s", e)
            self.enable_fallback()
            return self.update_note(note_id, title, content)

    def delete_note(self, note_id: int) -> bool:
        if self._should_use_fallback():
            return self._mem_store.pop(note_id, None) is not None
        try:
            note = db.session.get(Note, note_id)
            if not note:
                return False
            db.session.delete(note)
            db.session.commit()
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception("DB error on delete_note: %s", e)
            self.enable_fallback()
            return self.delete_note(note_id)

    def list_notes(self, page: int, page_size: int) -> Tuple[List[Note], int]:
        """Return (items, total) for pagination."""
        if self._should_use_fallback():
            items_all = list(self._mem_store.values())
            total = len(items_all)
            start = (page - 1) * page_size
            end = start + page_size
            page_items = items_all[start:end]
            class _Obj:
                def __init__(self, d): self._d = d
                def to_dict(self): return dict(self._d)
            return [ _Obj(d) for d in page_items ], total
        query = Note.query.order_by(Note.id.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total


# Singleton service accessor

_notes_service: NotesService | None = None

def get_notes_service() -> NotesService:
    global _notes_service
    if _notes_service is None:
        _notes_service = NotesService()
    return _notes_service
