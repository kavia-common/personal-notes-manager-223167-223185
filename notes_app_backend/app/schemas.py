from __future__ import annotations

from marshmallow import Schema, fields, validate


class NoteCreateSchema(Schema):
    """Schema for creating a note."""
    title = fields.String(required=True, validate=validate.Length(min=1), metadata={"description": "Note title (required, non-empty)"})
    content = fields.String(required=False, allow_none=True, metadata={"description": "Note content (optional)"})


class NoteUpdateSchema(Schema):
    """Schema for updating a note; title is required and non-empty if provided."""
    title = fields.String(required=False, validate=validate.Length(min=1), metadata={"description": "Note title (non-empty if provided)"})
    content = fields.String(required=False, allow_none=True, metadata={"description": "Note content (optional)"})


class NoteResponseSchema(Schema):
    """Schema representing a Note in responses."""
    id = fields.Integer(required=True)
    title = fields.String(required=True)
    content = fields.String(allow_none=True)
    created_at = fields.String(required=True)
    updated_at = fields.String(required=True)


class PaginationQuerySchema(Schema):
    """Query params for pagination."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1), metadata={"description": "Page number (>=1). Default 1"})
    page_size = fields.Integer(load_default=10, validate=validate.Range(min=1, max=100), metadata={"description": "Page size (1-100). Default 10"})


class PaginatedNotesResponseSchema(Schema):
    """Response schema for paginated list of notes."""
    data = fields.List(fields.Nested(NoteResponseSchema))
    pagination = fields.Dict(keys=fields.String(), values=fields.Integer())
