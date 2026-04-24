"""Unit tests for summarizer core utilities (no model loading required)."""
from summarizer.ingestion import clean_text
from summarizer.evaluation import compute_rouge, evaluate_single


def test_clean_text_collapses_whitespace():
    assert clean_text("hello   world") == "hello world"


def test_clean_text_strips():
    assert clean_text("  hi  ") == "hi"


def test_clean_text_collapses_newlines():
    text = "line1\n\n\n\nline2"
    result = clean_text(text)
    assert "\n\n\n" not in result


def test_compute_rouge_identical():
    text = "The scientists discovered a new carbon capture method."
    scores = compute_rouge([text], [text])
    assert scores["rouge1"] == 1.0
    assert scores["rougeL"] == 1.0


def test_compute_rouge_different():
    pred = "The researchers found a new climate solution."
    ref = "Scientists discovered a revolutionary carbon capture method."
    scores = compute_rouge([pred], [ref])
    assert 0 <= scores["rouge1"] <= 1
    assert 0 <= scores["rouge2"] <= 1


def test_evaluate_single_fields():
    summary = "Scientists found a new method for capturing carbon dioxide at scale."
    reference = "Researchers discovered a new carbon capture method that works at large scale."
    result = evaluate_single(summary, reference)
    assert hasattr(result, "rouge1")
    assert hasattr(result, "rouge2")
    assert hasattr(result, "rougeL")
    assert hasattr(result, "compression_ratio")
    assert hasattr(result, "avg_sentence_length")
    assert 0 <= result.rouge1 <= 1
    assert result.compression_ratio > 0


def test_evaluate_single_identical():
    text = "The quick brown fox jumps over the lazy dog in the field."
    result = evaluate_single(text, text)
    assert result.rouge1 == 1.0
    assert result.rougeL == 1.0
