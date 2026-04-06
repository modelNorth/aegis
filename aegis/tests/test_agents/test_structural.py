"""Tests for StructuralAgent."""

import pytest
from aegis.agents.structural import StructuralAgent
from aegis.core.constants import ContentType


@pytest.fixture
def agent() -> StructuralAgent:
    return StructuralAgent(enable_memory=False)


def test_clean_text_low_score(agent: StructuralAgent) -> None:
    context = {
        "content_type": ContentType.TEXT.value,
        "processed": {
            "zero_width_chars": [],
            "homoglyphs_detected": False,
            "encoding_tricks": [],
        },
    }
    finding = agent.analyze("Normal clean text", context)
    assert finding.score < 0.3
    assert finding.agent == "structural"


def test_zero_width_char_detected(agent: StructuralAgent) -> None:
    context = {
        "content_type": ContentType.TEXT.value,
        "processed": {
            "zero_width_chars": ["U+200B"],
            "homoglyphs_detected": False,
            "encoding_tricks": [],
        },
    }
    finding = agent.analyze("Hello\u200bWorld", context)
    assert finding.score > 0.0
    assert any("zero_width" in s for s in finding.signals)


def test_hidden_html_elements(agent: StructuralAgent) -> None:
    context = {
        "content_type": ContentType.HTML.value,
        "processed": {
            "hidden_elements": [
                {"tag": "div", "reason": "css_display", "text": "Hidden injection"}
            ],
            "zero_width_chars": [],
            "comments": [],
            "css_tricks": [],
            "data_attributes": [],
            "encoding_tricks": [],
        },
    }
    finding = agent.analyze("<html>...</html>", context)
    assert finding.score > 0.0
    assert any("hidden_elements" in s for s in finding.signals)


def test_pdf_embedded_js_high_score(agent: StructuralAgent) -> None:
    context = {
        "content_type": ContentType.PDF.value,
        "processed": {
            "has_embedded_js": True,
            "has_embedded_files": False,
            "zero_width_chars": [],
            "metadata": {},
        },
    }
    finding = agent.analyze("pdf_content", context)
    assert finding.score >= 0.5
    assert "pdf_embedded_javascript" in finding.signals


def test_finding_has_required_fields(agent: StructuralAgent) -> None:
    context = {
        "content_type": ContentType.TEXT.value,
        "processed": {
            "zero_width_chars": [],
            "homoglyphs_detected": False,
            "encoding_tricks": [],
        },
    }
    finding = agent.analyze("test", context)
    assert 0.0 <= finding.score <= 1.0
    assert isinstance(finding.signals, list)
    assert isinstance(finding.explanation, str)
    assert finding.agent == "structural"
