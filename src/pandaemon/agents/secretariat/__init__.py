"""Secretariat agent - Obsidian vault manager."""

from pandaemon.agents.secretariat.agent import SecretariatAgent
from pandaemon.agents.secretariat.schemas import CreateNoteRequest, NoteResponse, SearchNotesRequest

__all__ = ["SecretariatAgent", "CreateNoteRequest", "NoteResponse", "SearchNotesRequest"]
