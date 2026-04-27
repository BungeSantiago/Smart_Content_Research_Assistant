"""Tests del parser de comandos humanos."""
from core.human_parser import parse_human_input


def test_approve_simple():
    fb = parse_human_input("approve 1,3")
    assert fb.approved_ids == [1, 3]
    assert not fb.rejected_ids


def test_reject_simple():
    fb = parse_human_input("reject 2")
    assert fb.rejected_ids == [2]


def test_modify():
    fb = parse_human_input("modify 1 to 'AI ethical frameworks'")
    assert fb.modifications == {1: "ai ethical frameworks"}


def test_add():
    fb = parse_human_input("add 'AI safety concerns'")
    assert fb.additions == ["ai safety concerns"]


def test_combined():
    fb = parse_human_input(
        "approve 1,3, reject 2, add 'AI safety', modify 4 to 'Deep learning'"
    )
    assert fb.approved_ids == [1, 3]
    assert fb.rejected_ids == [2]
    assert fb.additions == ["ai safety"]
    assert fb.modifications == {4: "deep learning"}


def test_empty():
    fb = parse_human_input("")
    assert fb.is_empty