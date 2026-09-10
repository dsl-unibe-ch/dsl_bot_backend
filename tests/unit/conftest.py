"""Unit-test conftest: shared state and behavioural regression metrics reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest as _pytest


def pytest_configure(config: _pytest.Config) -> None:
    """Initialise shared store for regression test results."""
    config._regression_results: list[dict] = []  # type: ignore[attr-defined]


def _precision_recall_f1(
    labels: list[str],
    predicted: list[str | None],
    actual: list[str],
) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for label in labels:
        tp = sum(1 for p, a in zip(predicted, actual) if p == label and a == label)
        fp = sum(1 for p, a in zip(predicted, actual) if p == label and a != label)
        fn = sum(1 for p, a in zip(predicted, actual) if p != label and a == label)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        stats[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": float(tp + fn),
        }
    return stats


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:  # noqa: ARG001
    """Print behavioural regression metrics after the test run."""
    results: list[dict] = getattr(config, "_regression_results", [])
    if not results:
        return

    terminalreporter.write_sep("-", "Behavioural Regression Metrics")
    terminalreporter.write_line(f"Total regression cases evaluated: {len(results)}")

    # ── Scope label ──────────────────────────────────────────────────────────
    scope_pairs = [
        (r["expected_scope"], r["actual_scope"])
        for r in results
        if r.get("actual_scope") is not None
    ]
    if scope_pairs:
        scope_expected, scope_actual = zip(*scope_pairs)
        scope_acc = sum(e == a for e, a in scope_pairs) / len(scope_pairs)
        terminalreporter.write_line(
            f"\nScope accuracy: {scope_acc:.2%}  ({len(scope_pairs)} cases)"
        )
        scope_labels = ["in_scope", "out_of_scope", "unclear"]
        stats = _precision_recall_f1(
            scope_labels, list(scope_actual), list(scope_expected)
        )
        header = f"  {'Label':<22} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}"
        terminalreporter.write_line(header)
        for label in scope_labels:
            s = stats[label]
            terminalreporter.write_line(
                f"  {label:<22} {s['precision']:>10.2%} {s['recall']:>10.2%}"
                f" {s['f1']:>10.2%} {int(s['support']):>10}"
            )

    # ── Language match ────────────────────────────────────────────────────────
    lang_pairs = [
        (r["expected_language"], r["actual_language"])
        for r in results
        if r.get("actual_language") is not None
    ]
    if lang_pairs:
        lang_acc = sum(e == a for e, a in lang_pairs) / len(lang_pairs)
        terminalreporter.write_line(
            f"\nLanguage-match accuracy: {lang_acc:.2%}  ({len(lang_pairs)} cases)"
        )

    # ── Retrieval appropriateness ────────────────────────────────────────────
    ret_pairs = [
        (r["expected_retrieve"], r["actual_retrieve"])
        for r in results
        if r.get("expected_retrieve") is not None
        and r.get("actual_retrieve") is not None
    ]
    if ret_pairs:
        ret_acc = sum(e == a for e, a in ret_pairs) / len(ret_pairs)
        terminalreporter.write_line(
            f"\nRetrieval-appropriateness accuracy: {ret_acc:.2%}  ({len(ret_pairs)} cases)"
        )
