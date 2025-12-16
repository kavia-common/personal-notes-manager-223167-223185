from __future__ import annotations

from math import ceil

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..schemas import (
    NoteCreateSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
    PaginationQuerySchema,
    PaginatedNotesResponseSchema,
)
from ..services import get_notes_service

blp = Blueprint(
    "Notes",
    "notes",
    url_prefix="/notes",
    description="CRUD operations for personal notes",
)


def pagination_meta(total: int, page: int, page_size: int) -> dict:
    total_pages = max(ceil(total / page_size), 1) if page_size else 1
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None
    return {
        "total": total,
        "total_pages": total_pages,
        "first_page": 1,
        "last_page": total_pages,
        "page": page,
        "previous_page": prev_page,
        "next_page": next_page,
    }


@blp.route("/")
class NotesList(MethodView):
    @blp.arguments(PaginationQuerySchema, location="query")
    @blp.response(200, PaginatedNotesResponseSchema)
    @blp.doc(
        summary="List notes",
        description="Returns a paginated list of notes. Use page and page_size query params."
    )
    def get(self, args):
        """List notes with pagination."""
        svc = get_notes_service()
        page = args.get("page", 1)
        page_size = args.get("page_size", 10)
        items, total = svc.list_notes(page=page, page_size=page_size)
        return {
            "data": [n.to_dict() for n in items],
            "pagination": pagination_meta(total, page, page_size),
        }

    @blp.arguments(NoteCreateSchema)
    @blp.response(201, NoteResponseSchema)
    @blp.doc(
        summary="Create note",
        description="Create a new note with title (required) and optional content."
    )
    def post(self, json_body):
        """Create a new note."""
        title = json_body.get("title")
        if title is None or (isinstance(title, str) and title.strip() == ""):
            abort(400, message="title is required and must be non-empty")
        content = json_body.get("content")
        note = get_notes_service().create_note(title=title.strip(), content=content)
        return note.to_dict()


@blp.route("/<int:note_id>")
class NoteDetail(MethodView):
    @blp.response(200, NoteResponseSchema)
    @blp.doc(
        summary="Get note by ID",
        description="Retrieve a single note by its ID."
    )
    def get(self, note_id: int):
        """Get a single note."""
        note = get_notes_service().get_note(note_id)
        if not note:
            abort(404, message="Note not found")
        return note.to_dict()

    @blp.arguments(NoteUpdateSchema)
    @blp.response(200, NoteResponseSchema)
    @blp.doc(
        summary="Update note",
        description="Update note title/content. At least one field must be provided."
    )
    def put(self, json_body, note_id: int):
        """Update a note."""
        if not json_body:
            abort(400, message="Request body cannot be empty")
        if "title" in json_body:
            title = json_body.get("title")
            if title is not None and isinstance(title, str) and title.strip() == "":
                abort(400, message="title must be non-empty if provided")
        updated = get_notes_service().update_note(
            note_id,
            title=(json_body.get("title").strip() if isinstance(json_body.get("title"), str) else json_body.get("title")),
            content=json_body.get("content"),
        )
        if not updated:
            abort(404, message="Note not found")
        return updated.to_dict()

    @blp.response(204)
    @blp.doc(
        summary="Delete note",
        description="Delete a note by its ID."
    )
    def delete(self, note_id: int):
        """Delete a note."""
        ok = get_notes_service().delete_note(note_id)
        if not ok:
            abort(404, message="Note not found")
        return "", 204
