"""Tests for Filler.fill_form's value-to-widget matching (issue #642).

Widgets are matched to LLM answers by field NAME, not by position — the
field-dict order and the PDF's physical widget order aren't guaranteed to
align.
"""

from unittest.mock import MagicMock, patch

from app.services.filler import Filler


class _FakeAnnot:
    """Stand-in for a pdfrw widget annotation."""

    def __init__(self, name, rect):
        self.Subtype = "/Widget"
        self.T = name
        self.Rect = rect
        self.V = None
        self.AP = "placeholder-appearance"


class _FakePage:
    def __init__(self, annots):
        self.Annots = annots


class _FakePdf:
    def __init__(self, pages):
        self.pages = pages


class _FakeLLM:
    """Stand-in for app.services.llm.LLM — main_loop() returns self, like the real one."""

    def __init__(self, data: dict):
        self._data = data

    def main_loop(self):
        return self

    def get_data(self):
        return self._data


class TestFillerNameMatching:

    def _run(self, annots, answers):
        fake_pdf = _FakePdf(pages=[_FakePage(annots)])
        with patch("app.services.filler.PdfReader", return_value=fake_pdf), \
             patch("app.services.filler.PdfWriter") as mock_writer_cls:
            mock_writer_cls.return_value = MagicMock()
            Filler().fill_form(pdf_form="src/inputs/template.pdf", llm=_FakeLLM(answers))

    def test_values_match_by_name_when_widget_order_diverges_from_field_order(self):
        """Field dict is keyed a, b, c (insertion order) but the widgets sit on
        the page in physical order c, b, a (top-to-bottom). Positional matching
        would zip answers_list[0]="AAA" onto the first-visited widget (c's box)
        and answers_list[2]="CCC" onto the last (a's box) — wrong. Name matching
        must put each value in its own-named box regardless of page order."""
        annot_c = _FakeAnnot("c", rect=[0, 300, 100, 320])  # topmost
        annot_b = _FakeAnnot("b", rect=[0, 200, 100, 220])  # middle
        annot_a = _FakeAnnot("a", rect=[0, 100, 100, 120])  # bottommost

        # Physical/traversal order on the page: c, b, a.
        # Field-dict / answer order: a, b, c.
        answers = {"a": "AAA", "b": "BBB", "c": "CCC"}
        self._run([annot_c, annot_b, annot_a], answers)

        assert annot_a.V == "AAA"
        assert annot_b.V == "BBB"
        assert annot_c.V == "CCC"

    def test_widget_with_no_matching_answer_is_left_unfilled(self):
        annot_a = _FakeAnnot("a", rect=[0, 100, 100, 120])
        annot_d = _FakeAnnot("d", rect=[0, 200, 100, 220])

        self._run([annot_a, annot_d], {"a": "AAA"})

        assert annot_a.V == "AAA"
        assert annot_d.V is None

    def test_answer_with_no_matching_widget_does_not_crash(self):
        annot_a = _FakeAnnot("a", rect=[0, 100, 100, 120])

        # "extra" has no corresponding widget on the page.
        self._run([annot_a], {"a": "AAA", "extra": "unused"})

        assert annot_a.V == "AAA"
