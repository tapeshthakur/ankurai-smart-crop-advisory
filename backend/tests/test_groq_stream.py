from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import groq_service


class FakeStream:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self.lines)


def test_stream_yields_only_assistant_text(monkeypatch):
    monkeypatch.setattr(groq_service, "settings", SimpleNamespace(groq_api_key="test", groq_model="model", groq_timeout_seconds=2))
    monkeypatch.setattr(groq_service.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeStream([
        b'data: {"choices":[{"delta":{"content":"Check "}}]}\n',
        b'data: {"choices":[{"delta":{"content":"soil moisture."}}]}\n',
        b"data: [DONE]\n",
    ]))
    assert list(groq_service.stream_groq_farmer_assistant("What next?")) == ["Check ", "soil moisture."]


def test_stream_requires_configured_provider(monkeypatch):
    monkeypatch.setattr(groq_service, "settings", SimpleNamespace(groq_api_key="", groq_model="model", groq_timeout_seconds=2))
    with pytest.raises(groq_service.GroqServiceError, match="not configured"):
        list(groq_service.stream_groq_farmer_assistant("Hello"))
