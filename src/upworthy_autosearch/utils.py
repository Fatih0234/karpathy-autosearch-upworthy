"""Shared utilities."""
from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STRATEGY_FILE = Path(__file__).parents[2] / "strategy.md"
RESULTS_DIR = Path(__file__).parents[2] / "results"
RESULTS_TSV = RESULTS_DIR / "results.tsv"
ITERATION_FILE = RESULTS_DIR / "iteration.txt"
EXPERIMENT_LOG = RESULTS_DIR / "experiment_log.md"
LEADERBOARD_MD = RESULTS_DIR / "leaderboard.md"
ANALYSIS_SUMMARY_MD = RESULTS_DIR / "analysis_summary.md"
EXTENDED_ANALYSIS_MD = RESULTS_DIR / "extended_analysis.md"
METRICS_CSV = RESULTS_DIR / "metrics.csv"
ACCURACY_SVG = RESULTS_DIR / "accuracy_over_time.svg"
LOG_LOSS_SVG = RESULTS_DIR / "log_loss_over_time.svg"
LEGACY_RESULTS_COLUMNS = [
    "timestamp",
    "split",
    "accuracy",
    "log_loss",
    "n_pairs",
    "strategy_hash",
    "notes",
]
RESULTS_COLUMNS = LEGACY_RESULTS_COLUMNS + ["provider", "iteration", "key_change"]


def strategy_hash() -> str:
    """SHA-256 of strategy.md (first 16 hex chars)."""
    if not STRATEGY_FILE.exists():
        return "no-strategy"
    content = STRATEGY_FILE.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def get_and_increment_iteration() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    n = int(ITERATION_FILE.read_text().strip()) if ITERATION_FILE.exists() else 0
    n += 1
    ITERATION_FILE.write_text(str(n))
    return n


def append_experiment_log(
    *,
    iteration: int,
    experiment_id: str,
    strategy_hash_val: str,
    key_change: str,
    acc_before: float,
    acc_after: float,
    ll_before: float,
    ll_after: float,
    verdict: str,
    rationale: str,
) -> None:
    if not EXPERIMENT_LOG.exists():
        EXPERIMENT_LOG.write_text("# Experiment Log\n\n")
    badge = "✅ IMPROVED" if verdict == "IMPROVED" else "❌ REJECTED"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"## Iteration {iteration} — {badge}\n\n"
        f"| Field | Value |\n|---|---|\n"
        f"| experiment_id | `{experiment_id}` |\n"
        f"| strategy_hash | `{strategy_hash_val}` |\n"
        f"| timestamp | {ts} |\n"
        f"| key_change | {key_change} |\n"
        f"| accuracy | {acc_before:.4f} → {acc_after:.4f} |\n"
        f"| log_loss | {ll_before:.4f} → {ll_after:.4f} |\n\n"
        f"**Rationale:** {rationale}\n\n---\n\n"
    )
    with open(EXPERIMENT_LOG, "a") as f:
        f.write(entry)


def _coerce_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_results_rows(tsv: Path | None = None) -> list[dict[str, Any]]:
    """Load results.tsv while tolerating legacy headers with newer appended rows."""
    path = tsv or RESULTS_TSV
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue

        fields = line.split("\t")
        if fields == LEGACY_RESULTS_COLUMNS or fields == RESULTS_COLUMNS:
            continue

        parsed_fields = list(fields[: len(RESULTS_COLUMNS)])
        if len(fields) > len(RESULTS_COLUMNS):
            parsed_fields[-1] = "\t".join(fields[len(RESULTS_COLUMNS) - 1 :])

        raw_row = {column: "" for column in RESULTS_COLUMNS}
        for index, value in enumerate(parsed_fields):
            raw_row[RESULTS_COLUMNS[index]] = value

        accuracy = _coerce_float(raw_row["accuracy"])
        log_loss = _coerce_float(raw_row["log_loss"])
        n_pairs = _coerce_int(raw_row["n_pairs"])
        if accuracy is None or log_loss is None or n_pairs is None:
            continue

        iteration = _coerce_int(raw_row["iteration"])
        rows.append(
            {
                "timestamp": raw_row["timestamp"],
                "split": raw_row["split"],
                "accuracy": accuracy,
                "log_loss": log_loss,
                "n_pairs": n_pairs,
                "strategy_hash": raw_row["strategy_hash"],
                "notes": raw_row["notes"],
                "provider": raw_row["provider"] or "—",
                "iteration": iteration if iteration is not None else "—",
                "key_change": raw_row["key_change"],
            }
        )

    return rows


def get_best_dev_metrics(
    tsv: Path | None = None,
    *,
    provider: str | None = None,
    n_pairs: int | None = None,
) -> tuple[float, float]:
    """Return best dev accuracy and best dev log loss from parsed results."""
    rows = [row for row in load_results_rows(tsv) if row["split"] == "dev"]
    if provider is not None:
        rows = [row for row in rows if row["provider"] == provider]
    if n_pairs is not None:
        rows = [row for row in rows if row["n_pairs"] == n_pairs]
    if not rows:
        return 0.0, float("inf")
    best_accuracy = max(row["accuracy"] for row in rows)
    best_log_loss = min(row["log_loss"] for row in rows)
    return best_accuracy, best_log_loss


def _select_primary_dev_cohort(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the dominant provider/n_pairs cohort for cross-run reporting."""
    if not rows:
        return None

    cohorts = Counter((row["provider"], row["n_pairs"]) for row in rows)
    latest_timestamps = {
        cohort: max(str(row["timestamp"]) for row in rows if (row["provider"], row["n_pairs"]) == cohort)
        for cohort in cohorts
    }
    provider, n_pairs = max(
        cohorts,
        key=lambda cohort: (
            cohorts[cohort],
            cohort[1],
            latest_timestamps[cohort],
            cohort[0],
        ),
    )
    return {
        "provider": provider,
        "n_pairs": n_pairs,
        "run_count": cohorts[(provider, n_pairs)],
    }


def _filter_rows_to_cohort(rows: list[dict[str, Any]], cohort: dict[str, Any] | None) -> list[dict[str, Any]]:
    if cohort is None:
        return []
    return [
        row
        for row in rows
        if row["provider"] == cohort["provider"] and row["n_pairs"] == cohort["n_pairs"]
    ]


def _format_cohort_label(cohort: dict[str, Any]) -> str:
    return f"provider={cohort['provider']}, n_pairs={cohort['n_pairs']}"


def regenerate_leaderboard() -> None:
    all_rows = [row for row in load_results_rows() if row["split"] == "dev"]
    cohort = _select_primary_dev_cohort(all_rows)
    rows = _filter_rows_to_cohort(all_rows, cohort)
    if not rows or cohort is None:
        return

    rows.sort(key=lambda row: (-row["accuracy"], row["log_loss"], str(row["timestamp"])))
    lines = [
        "# Leaderboard\n",
        (
            "Auto-generated. Sorted by dev accuracy descending for the primary reporting cohort "
            f"({_format_cohort_label(cohort)}; {len(rows)}/{len(all_rows)} dev runs).\n\n"
        ),
        "| Rank | Accuracy | Log Loss | Iteration | Provider | N Pairs | Experiment ID | Timestamp |",
        "|------|----------|----------|-----------|----------|---------|---------------|-----------|",
    ]
    for i, row in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {row['accuracy']:.4f} | {row['log_loss']:.4f} "
            f"| {row['iteration']} | {row['provider']} | {row['n_pairs']} "
            f"| {row['notes'] or '—'} | {str(row['timestamp'])[:16]} |"
        )
    LEADERBOARD_MD.write_text("\n".join(lines) + "\n")


def _sort_results_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[str, float]:
        iteration = row["iteration"] if isinstance(row["iteration"], int) else math.inf
        return str(row["timestamp"]), iteration

    return sorted(rows, key=sort_key)


def _enrich_dev_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    running_best = float("-inf")
    for seq, row in enumerate(_sort_results_rows(rows), start=1):
        improved = row["accuracy"] > running_best
        running_best = max(running_best, row["accuracy"])
        enriched.append(
            {
                **row,
                "sequence": seq,
                "is_improvement": improved,
                "running_best_accuracy": running_best,
            }
        )
    return enriched


def _write_metrics_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "sequence",
        "timestamp",
        "split",
        "accuracy",
        "log_loss",
        "n_pairs",
        "strategy_hash",
        "notes",
        "provider",
        "iteration",
        "key_change",
        "is_improvement",
        "running_best_accuracy",
    ]
    with open(METRICS_CSV, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _svg_line_chart(
    rows: list[dict[str, Any]],
    metric_key: str,
    title: str,
    color: str,
) -> str:
    width = 960
    height = 360
    left = 64
    right = 24
    top = 48
    bottom = 48
    inner_width = width - left - right
    inner_height = height - top - bottom

    x_values = [row["sequence"] for row in rows]
    y_values = [float(row[metric_key]) for row in rows]
    min_y = min(y_values)
    max_y = max(y_values)
    if math.isclose(min_y, max_y):
        padding = 0.05 if max_y == 0 else abs(max_y) * 0.05
        min_y -= padding
        max_y += padding
    else:
        padding = (max_y - min_y) * 0.1
        min_y -= padding
        max_y += padding

    def x_pos(value: int) -> float:
        if len(x_values) == 1:
            return left + inner_width / 2
        return left + ((value - 1) / (len(x_values) - 1)) * inner_width

    def y_pos(value: float) -> float:
        ratio = (value - min_y) / (max_y - min_y)
        return top + inner_height - ratio * inner_height

    line_points = " ".join(f"{x_pos(row['sequence']):.1f},{y_pos(float(row[metric_key])):.1f}" for row in rows)
    point_elements = []
    for row in rows:
        point_color = "#16803c" if row["is_improvement"] else color
        point_elements.append(
            f"<circle cx='{x_pos(row['sequence']):.1f}' cy='{y_pos(float(row[metric_key])):.1f}' r='4' fill='{point_color}' />"
        )

    x_tick_step = max(1, len(rows) // 8)
    x_ticks = []
    for idx in range(1, len(rows) + 1, x_tick_step):
        x = x_pos(idx)
        x_ticks.append(
            f"<text x='{x:.1f}' y='{height - 18}' text-anchor='middle' font-size='12' fill='#475569'>{idx}</text>"
        )

    y_ticks = []
    for tick in range(5):
        value = min_y + ((max_y - min_y) * tick / 4)
        y = y_pos(value)
        y_ticks.append(f"<line x1='{left}' y1='{y:.1f}' x2='{width - right}' y2='{y:.1f}' stroke='#e2e8f0' />")
        y_ticks.append(
            f"<text x='{left - 10}' y='{y + 4:.1f}' text-anchor='end' font-size='12' fill='#475569'>{value:.3f}</text>"
        )

    return "\n".join(
        [
            f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
            "<rect width='100%' height='100%' fill='#ffffff' />",
            f"<text x='{left}' y='28' font-size='20' font-family='Arial, sans-serif' fill='#0f172a'>{title}</text>",
            f"<text x='{width - right}' y='28' text-anchor='end' font-size='12' font-family='Arial, sans-serif' fill='#475569'>Green dots mark new best accuracy</text>",
            *y_ticks,
            f"<line x1='{left}' y1='{top + inner_height}' x2='{width - right}' y2='{top + inner_height}' stroke='#94a3b8' />",
            f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{line_points}' />",
            *point_elements,
            *x_ticks,
            f"<text x='{width / 2:.1f}' y='{height - 4}' text-anchor='middle' font-size='12' fill='#475569'>Run sequence</text>",
            "</svg>",
        ]
    )


def _write_extended_analysis(enriched_rows: list[dict[str, Any]]) -> None:
    """Write extended_analysis.md with histograms, rolling averages, and improvement stats."""
    if not enriched_rows:
        return

    bands = [
        ("[0.65+)", 0.65, float("inf")),
        ("[0.60-0.65)", 0.60, 0.65),
        ("[0.55-0.60)", 0.55, 0.60),
        ("[0.50-0.55)", 0.50, 0.55),
        ("[<0.50)", float("-inf"), 0.50),
    ]

    total = len(enriched_rows)
    improvement_rate = sum(1 for r in enriched_rows if r["is_improvement"]) / total * 100 if total else 0.0

    histogram_lines = ["## Accuracy Band Histogram", "", "| Band | Count | % | Best Log Loss |", "|------|-------|---|---------------|"]
    for label, lo, hi in bands:
        band_rows = [r for r in enriched_rows if lo <= r["accuracy"] < hi]
        count = len(band_rows)
        pct = count / total * 100 if total else 0.0
        best_ll = min((r["log_loss"] for r in band_rows), default=float("nan"))
        best_ll_str = f"{best_ll:.4f}" if not math.isnan(best_ll) else "—"
        histogram_lines.append(f"| {label} | {count} | {pct:.1f}% | {best_ll_str} |")

    window = 10
    rolling_lines = ["", "## Rolling 10-Run Average Accuracy", "", "| Run | Accuracy | Rolling Avg |", "|-----|----------|-------------|"]
    for i, row in enumerate(enriched_rows):
        window_rows = enriched_rows[max(0, i - window + 1): i + 1]
        avg = sum(r["accuracy"] for r in window_rows) / len(window_rows)
        rolling_lines.append(f"| {row['sequence']} | {row['accuracy']:.4f} | {avg:.4f} |")

    top_rows = sorted(enriched_rows, key=lambda r: (-r["accuracy"], r["log_loss"]))[:10]
    top_lines = ["", "## Top-10 Runs by Accuracy", "", "| Rank | Seq | Accuracy | Log Loss | Key Change |", "|------|-----|----------|----------|------------|"]
    for rank, r in enumerate(top_rows, 1):
        key = (r["key_change"] or "—")[:60]
        top_lines.append(f"| {rank} | {r['sequence']} | {r['accuracy']:.4f} | {r['log_loss']:.4f} | {key} |")

    cohort = {
        "provider": enriched_rows[0]["provider"],
        "n_pairs": enriched_rows[0]["n_pairs"],
    }
    lines = [
        "# Extended Analysis",
        "",
        f"- Reporting cohort: {_format_cohort_label(cohort)}",
        f"- Total dev runs: {total}",
        f"- Improvement rate: {improvement_rate:.1f}%",
        "",
        *histogram_lines,
        *rolling_lines,
        *top_lines,
        "",
    ]
    EXTENDED_ANALYSIS_MD.write_text("\n".join(lines) + "\n")


def regenerate_analysis_artifacts() -> None:
    all_rows = [row for row in load_results_rows() if row["split"] == "dev"]
    cohort = _select_primary_dev_cohort(all_rows)
    rows = _filter_rows_to_cohort(all_rows, cohort)
    if not rows or cohort is None:
        return

    enriched_rows = _enrich_dev_rows(rows)
    _write_metrics_csv(enriched_rows)

    best_row = min(
        enriched_rows,
        key=lambda row: (-row["accuracy"], row["log_loss"], str(row["timestamp"])),
    )
    latest_row = enriched_rows[-1]
    improved_count = sum(1 for row in enriched_rows if row["is_improvement"])
    summary_lines = [
        "# Experiment Analysis",
        "",
        f"- Total dev runs: {len(all_rows)}",
        f"- Reporting cohort: {_format_cohort_label(cohort)} ({len(enriched_rows)} runs)",
        f"- Improvements in reporting cohort: {improved_count}",
        f"- Best accuracy: {best_row['accuracy']:.4f} (run {best_row['sequence']}, iteration {best_row['iteration']})",
        f"- Best log loss: {min(row['log_loss'] for row in enriched_rows):.4f}",
        f"- Latest accuracy: {latest_row['accuracy']:.4f}",
        f"- Latest log loss: {latest_row['log_loss']:.4f}",
        f"- Latest key change: {latest_row['key_change'] or '—'}",
        "",
        "Artifacts:",
        f"- metrics CSV: `{METRICS_CSV.name}`",
        f"- accuracy chart: `{ACCURACY_SVG.name}`",
        f"- log loss chart: `{LOG_LOSS_SVG.name}`",
    ]
    ANALYSIS_SUMMARY_MD.write_text("\n".join(summary_lines) + "\n")
    cohort_suffix = f"{cohort['provider']}, {cohort['n_pairs']} pairs"
    ACCURACY_SVG.write_text(
        _svg_line_chart(enriched_rows, "accuracy", f"Dev Accuracy by Run ({cohort_suffix})", "#2563eb")
    )
    LOG_LOSS_SVG.write_text(
        _svg_line_chart(enriched_rows, "log_loss", f"Dev Log Loss by Run ({cohort_suffix})", "#dc2626")
    )
    _write_extended_analysis(enriched_rows)
