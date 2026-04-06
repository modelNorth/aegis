"""HTML processor - parsing, hidden content detection, script analysis."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Comment, Tag

from aegis.core.constants import SUSPICIOUS_CSS_PATTERNS
from aegis.processors.text import TextProcessor


class HtmlProcessor:
    def __init__(self) -> None:
        self._text_processor = TextProcessor()

    def process(self, content: str) -> ProcessedHtml:
        soup = BeautifulSoup(content, "lxml")

        visible_text = self._extract_visible_text(soup)
        hidden_elements = self._find_hidden_elements(soup)
        comments = self._extract_comments(soup)
        scripts = self._extract_scripts(soup)
        meta_content = self._extract_meta_content(soup)
        data_attributes = self._find_suspicious_data_attrs(soup)
        css_tricks = self._find_css_tricks(soup)
        processed_text = self._text_processor.process(visible_text)

        all_text = " ".join([
            visible_text,
            " ".join(comments),
            " ".join(scripts),
            " ".join(meta_content),
        ])

        return ProcessedHtml(
            visible_text=visible_text,
            all_text=all_text,
            hidden_elements=hidden_elements,
            comments=comments,
            scripts=scripts,
            meta_content=meta_content,
            data_attributes=data_attributes,
            css_tricks=css_tricks,
            zero_width_chars=processed_text.zero_width_chars,
            homoglyphs_detected=processed_text.homoglyphs_detected,
            encoding_tricks=processed_text.encoding_tricks,
        )

    def _extract_visible_text(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "head", "meta", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    def _find_hidden_elements(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        hidden = []

        hidden_attrs = soup.find_all(attrs={"hidden": True})
        for el in hidden_attrs:
            if isinstance(el, Tag):
                hidden.append({"tag": el.name, "reason": "hidden_attribute", "text": el.get_text()[:200]})

        for el in soup.find_all(style=True):
            if isinstance(el, Tag):
                style = str(el.get("style", "")).lower().replace(" ", "")
                for pattern in SUSPICIOUS_CSS_PATTERNS:
                    if pattern.replace(" ", "") in style:
                        hidden.append({
                            "tag": el.name,
                            "reason": f"css_{pattern.split(':')[0].strip()}",
                            "text": el.get_text()[:200],
                        })
                        break

        aria_hidden = soup.find_all(attrs={"aria-hidden": "true"})
        for el in aria_hidden:
            if isinstance(el, Tag) and el.get_text().strip():
                hidden.append({"tag": el.name, "reason": "aria_hidden", "text": el.get_text()[:200]})

        return hidden

    def _extract_comments(self, soup: BeautifulSoup) -> list[str]:
        return [str(c).strip() for c in soup.find_all(string=lambda t: isinstance(t, Comment)) if str(c).strip()]

    def _extract_scripts(self, soup: BeautifulSoup) -> list[str]:
        scripts = []
        for script in soup.find_all("script"):
            if isinstance(script, Tag):
                text = script.get_text().strip()
                if text:
                    scripts.append(text[:500])
        return scripts

    def _extract_meta_content(self, soup: BeautifulSoup) -> list[str]:
        meta_content = []
        for meta in soup.find_all("meta"):
            if isinstance(meta, Tag):
                content = meta.get("content", "")
                if content and len(str(content)) > 10:
                    meta_content.append(str(content))
        return meta_content

    def _find_suspicious_data_attrs(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        suspicious = []
        injection_keywords = ["inject", "prompt", "system", "override", "ignore", "instruction"]
        for el in soup.find_all(True):
            if isinstance(el, Tag):
                for attr, value in el.attrs.items():
                    if attr.startswith("data-"):
                        val_str = str(value).lower()
                        if any(kw in val_str for kw in injection_keywords):
                            suspicious.append({"attribute": attr, "value": str(value)[:200]})
        return suspicious

    def _find_css_tricks(self, soup: BeautifulSoup) -> list[str]:
        tricks = []
        for style_tag in soup.find_all("style"):
            if isinstance(style_tag, Tag):
                text = style_tag.get_text()
                if re.search(r"color\s*:\s*white|color\s*:\s*#fff|font-size\s*:\s*0", text, re.I):
                    tricks.append("css_invisible_text")
                if re.search(r"position\s*:\s*absolute.*left\s*:\s*-\d+", text, re.I | re.S):
                    tricks.append("css_offscreen_content")
        return tricks


class ProcessedHtml:
    def __init__(
        self,
        visible_text: str,
        all_text: str,
        hidden_elements: list[dict[str, Any]],
        comments: list[str],
        scripts: list[str],
        meta_content: list[str],
        data_attributes: list[dict[str, str]],
        css_tricks: list[str],
        zero_width_chars: list[str],
        homoglyphs_detected: bool,
        encoding_tricks: list[str],
    ) -> None:
        self.visible_text = visible_text
        self.all_text = all_text
        self.hidden_elements = hidden_elements
        self.comments = comments
        self.scripts = scripts
        self.meta_content = meta_content
        self.data_attributes = data_attributes
        self.css_tricks = css_tricks
        self.zero_width_chars = zero_width_chars
        self.homoglyphs_detected = homoglyphs_detected
        self.encoding_tricks = encoding_tricks

    def to_dict(self) -> dict:
        return {
            "visible_text": self.visible_text,
            "all_text": self.all_text,
            "hidden_elements": self.hidden_elements,
            "comments": self.comments,
            "scripts": self.scripts,
            "meta_content": self.meta_content,
            "data_attributes": self.data_attributes,
            "css_tricks": self.css_tricks,
            "zero_width_chars": self.zero_width_chars,
            "homoglyphs_detected": self.homoglyphs_detected,
            "encoding_tricks": self.encoding_tricks,
        }
