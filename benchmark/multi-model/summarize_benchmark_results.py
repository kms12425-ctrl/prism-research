from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "benchmark-results"

SMOKE_1_PATH = RESULTS_DIR / \
    "synthetic_num_models-1_req_rate-1_duration-60_alpha-2.1_cv-1_slo-10_key_metrics.tsv"
SMOKE_2_PATH = RESULTS_DIR / \
    "synthetic_num_models-2_req_rate-1_duration-60_alpha-2.1_cv-1_slo-10_key_metrics.tsv"
STATIC_SINGLE_PATH = RESULTS_DIR / "step5_static_single_request.json"
OURS_SINGLE_PATH = RESULTS_DIR / "step5_ours_single_request.json"

SUMMARY_JSON_PATH = RESULTS_DIR / "step5_and_smoke_summary.json"
SUMMARY_MD_PATH = RESULTS_DIR / "step5_and_smoke_summary.md"
SUMMARY_SVG_PATH = RESULTS_DIR / "step5_and_smoke_comparison.svg"


def load_tsv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        rows = list(reader)
        if rows:
            return rows
        raise ValueError(f"No rows found in {path}")


def select_row(path: Path, exp_name: str | None = None) -> dict[str, str]:
    rows = load_tsv_rows(path)
    if exp_name is None:
        return rows[0]

    for row in rows:
        if row.get("exp_name") == exp_name:
            return row

    raise ValueError(f"Could not find exp_name={exp_name} in {path}")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def as_float(value) -> float | None:
    if value in (None, "", "null"):
        return None
    return float(value)


def compact_single_result(name: str, payload: dict) -> dict:
    error = payload.get("error") or ""
    error_summary = ""
    if error:
        lines = [line.strip() for line in error.splitlines() if line.strip()]
        if lines:
            error_summary = lines[-1]

    return {
        "name": name,
        "mode": payload.get("mode", name),
        "success": bool(payload.get("success")),
        "latency_ms": as_float(payload.get("mean_e2e_latency_ms")),
        "latency_server_ms": as_float(payload.get("latency_server_s")) * 1000.0
        if payload.get("latency_server_s") is not None
        else None,
        "ttft_ms": as_float(payload.get("mean_ttft_ms")),
        "tpot_ms": as_float(payload.get("mean_tpot_ms")),
        "wait_time_ms": as_float(payload.get("wait_time_s")) * 1000.0
        if payload.get("wait_time_s") is not None
        else None,
        "request_throughput": as_float(payload.get("request_throughput")),
        "output_len": int(payload.get("output_len", 0) or 0),
        "error_summary": error_summary,
        "error": error,
    }


def compact_smoke_result(row: dict[str, str], label: str) -> dict:
    return {
        "name": label,
        "exp_name": row["exp_name"],
        "mean_e2e_ms": float(row["Mean E2E Latency (s)"]) * 1000.0,
        "request_tput": float(row["Request Tput (req/s)"]),
        "mean_ttft_ms": float(row["Mean TTFT (s)"]) * 1000.0,
        "mean_tpot_ms": float(row["Mean TPOT (ms)"]),
        "mean_itl_ms": float(row["Mean ITL (ms)"]),
        "slo_attainment": float(row["SLO Attainment"]),
    }


def describe_single_request_outcome(static_single: dict, ours_single: dict) -> str:
    if static_single["success"] and ours_single["success"]:
        return "static and ours both succeeded, so the comparison is latency-vs-latency"
    if static_single["success"] and not ours_single["success"]:
        return "static baseline succeeded while ours failed to accept the request"
    if not static_single["success"] and ours_single["success"]:
        return "ours succeeded while the static baseline failed"
    return "both static and ours failed for the single-request check"


def build_notes(static_single: dict, ours_single: dict) -> list[str]:
    notes = [
        "Static single-request baseline was generated with benchmark/multi-model/model_configs/1_gpu_2_model_smoke_lowmem.json to fit the shared single A6000.",
    ]

    if ours_single["success"]:
        notes.append(
            "Ours single-request artifact also succeeded on port 30034, so the summary now reflects a direct latency-vs-latency comparison."
        )
    else:
        notes.append(
            "Ours single-request artifact remains a connection failure to 127.0.0.1:30034, so the comparison is success-vs-failure rather than latency-vs-latency."
        )

    return notes


def build_summary() -> dict:
    smoke_single = compact_smoke_result(
        select_row(SMOKE_1_PATH, "a6000_smoke_1model_baseline"), "baseline_1model"
    )
    smoke_two = compact_smoke_result(
        select_row(SMOKE_2_PATH, "a6000_smoke_2model_baseline"), "baseline_2model"
    )
    static_single = compact_single_result(
        "static_single_request", load_json(STATIC_SINGLE_PATH))
    ours_single = compact_single_result(
        "ours_single_request", load_json(OURS_SINGLE_PATH))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "smoke_1model": str(SMOKE_1_PATH.relative_to(ROOT.parent)),
            "smoke_2model": str(SMOKE_2_PATH.relative_to(ROOT.parent)),
            "static_single_request": str(STATIC_SINGLE_PATH.relative_to(ROOT.parent)),
            "ours_single_request": str(OURS_SINGLE_PATH.relative_to(ROOT.parent)),
            "static_server_config": "benchmark/multi-model/model_configs/1_gpu_2_model_smoke_lowmem.json",
        },
        "smoke_baseline": [smoke_single, smoke_two],
        "single_request": [static_single, ours_single],
        "highlights": {
            "single_request_outcome": describe_single_request_outcome(
                static_single, ours_single
            ),
            "static_single_request_latency_ms": static_single["latency_ms"],
            "static_single_request_ttft_ms": static_single["ttft_ms"],
            "two_model_smoke_request_tput": smoke_two["request_tput"],
            "two_model_smoke_mean_tpot_ms": smoke_two["mean_tpot_ms"],
        },
    }


def fmt_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def build_markdown(summary: dict) -> str:
    smoke_rows = summary["smoke_baseline"]
    single_rows = summary["single_request"]
    static_single, ours_single = single_rows

    lines = [
        "# Benchmark Summary",
        "",
        f"Generated at: {summary['generated_at']}",
        "",
        "## Smoke Baseline",
        "",
        "| Scenario | Mean E2E (ms) | Request Tput (req/s) | Mean TTFT (ms) | Mean TPOT (ms) | Mean ITL (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in smoke_rows:
        lines.append(
            "| {name} | {e2e} | {tput} | {ttft} | {tpot} | {itl} |".format(
                name=row["name"],
                e2e=fmt_number(row["mean_e2e_ms"]),
                tput=fmt_number(row["request_tput"], 3),
                ttft=fmt_number(row["mean_ttft_ms"]),
                tpot=fmt_number(row["mean_tpot_ms"]),
                itl=fmt_number(row["mean_itl_ms"]),
            )
        )

    lines.extend(
        [
            "",
            "## Single Request",
            "",
            "| Mode | Success | E2E (ms) | Server (ms) | TTFT (ms) | TPOT (ms) | Wait (ms) | Req Tput (req/s) | Error |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in single_rows:
        lines.append(
            "| {mode} | {success} | {e2e} | {server} | {ttft} | {tpot} | {wait} | {tput} | {error} |".format(
                mode=row["mode"],
                success="yes" if row["success"] else "no",
                e2e=fmt_number(row["latency_ms"]),
                server=fmt_number(row["latency_server_ms"]),
                ttft=fmt_number(row["ttft_ms"]),
                tpot=fmt_number(row["tpot_ms"]),
                wait=fmt_number(row["wait_time_ms"]),
                tput=fmt_number(row["request_throughput"], 3),
                error=(row["error_summary"] or "-").replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
        ]
    )

    lines.extend(
        f"- {note}" for note in build_notes(static_single, ours_single))

    return "\n".join(lines) + "\n"


def svg_rect(x: float, y: float, width: float, height: float, fill: str, rx: int = 10, stroke: str | None = None) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{rx}" fill="{fill}"{stroke_attr}/>'


def svg_text(x: float, y: float, text: str, size: int = 18, fill: str = "#1f2937", weight: str = "400") -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" '
        f'font-size="{size}" font-family="Verdana, sans-serif" font-weight="{weight}">{escaped}</text>'
    )


def build_svg(summary: dict) -> str:
    width = 1280
    height = 780
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f5f1e8"/>',
        svg_text(60, 70, "A6000 Benchmark Snapshot", 34, "#111827", "700"),
        svg_text(60, 102, "Smoke baseline metrics plus step5 single-request status",
                 18, "#4b5563", "400"),
        svg_rect(48, 130, 1184, 340, "#fffdf8", 18, "#d6d3d1"),
        svg_rect(48, 494, 1184, 238, "#fffdf8", 18, "#d6d3d1"),
        svg_text(78, 170, "Smoke Baseline", 24, "#111827", "700"),
        svg_text(78, 528, "Single Request", 24, "#111827", "700"),
    ]

    smoke_rows = summary["smoke_baseline"]
    smoke_metrics = [
        ("Mean E2E (ms)", [smoke_rows[0]["mean_e2e_ms"],
         smoke_rows[1]["mean_e2e_ms"]], "ms"),
        ("Request Tput (req/s)",
         [smoke_rows[0]["request_tput"], smoke_rows[1]["request_tput"]], "req/s"),
        ("Mean TTFT (ms)", [smoke_rows[0]["mean_ttft_ms"],
         smoke_rows[1]["mean_ttft_ms"]], "ms"),
        ("Mean TPOT (ms)", [smoke_rows[0]["mean_tpot_ms"],
         smoke_rows[1]["mean_tpot_ms"]], "ms"),
    ]
    metric_top = 214
    metric_gap = 70
    bar_left = 300
    bar_max_width = 820
    colors = ["#0f766e", "#d97706"]
    labels = [smoke_rows[0]["name"], smoke_rows[1]["name"]]

    parts.append(svg_text(78, 202, labels[0], 15, colors[0], "700"))
    parts.append(svg_text(240, 202, labels[1], 15, colors[1], "700"))

    for index, (metric_name, values, unit) in enumerate(smoke_metrics):
        y = metric_top + index * metric_gap
        max_value = max(values) if values else 1.0
        parts.append(svg_text(78, y + 22, metric_name, 18, "#1f2937", "600"))
        for value_index, value in enumerate(values):
            bar_y = y + value_index * 22
            bar_width = 0 if max_value == 0 else (
                value / max_value) * bar_max_width
            parts.append(svg_rect(bar_left, bar_y, bar_width,
                         16, colors[value_index], 8))
            parts.append(
                svg_text(
                    bar_left + min(bar_width + 14, bar_max_width + 320),
                    bar_y + 13,
                    f"{value:.2f} {unit}",
                    14,
                    "#374151",
                    "600",
                )
            )

    static_single, ours_single = summary["single_request"]
    ours_success = ours_single["success"]
    ours_fill = "#eff6ff" if ours_success else "#fff1f2"
    ours_stroke = "#bfdbfe" if ours_success else "#fecdd3"
    ours_title_fill = "#1d4ed8" if ours_success else "#9f1239"
    ours_body_fill = "#1e40af" if ours_success else "#881337"
    ours_status = "success" if ours_success else "failed"
    ours_line_one = (
        f"E2E {fmt_number(ours_single['latency_ms'])} ms"
        if ours_success
        else (ours_single["error_summary"] or "No error summary")
    )
    ours_line_two = (
        f"TTFT {fmt_number(ours_single['ttft_ms'])} ms, Req Tput {fmt_number(ours_single['request_throughput'], 3)} req/s"
        if ours_success
        else "No single-request latency available because the server was unreachable."
    )
    parts.extend(
        [
            svg_rect(80, 556, 540, 140, "#ecfdf5", 16, "#a7f3d0"),
            svg_text(108, 592, "Static baseline", 22, "#065f46", "700"),
            svg_text(108, 624, "success", 18, "#047857", "700"),
            svg_text(
                108, 654, f"E2E {fmt_number(static_single['latency_ms'])} ms", 18, "#065f46", "600"),
            svg_text(
                308, 654, f"TTFT {fmt_number(static_single['ttft_ms'])} ms", 18, "#065f46", "600"),
            svg_text(
                108, 684, f"TPOT {fmt_number(static_single['tpot_ms'])} ms", 18, "#065f46", "600"),
            svg_text(
                308, 684, f"Req Tput {fmt_number(static_single['request_throughput'], 3)} req/s", 18, "#065f46", "600"),
            svg_rect(660, 556, 540, 140, ours_fill, 16, ours_stroke),
            svg_text(688, 592, "Ours", 22, ours_title_fill, "700"),
            svg_text(688, 624, ours_status, 18, ours_title_fill, "700"),
            svg_text(688, 654, ours_line_one, 16, ours_body_fill, "600"),
            svg_text(688, 684, ours_line_two, 16, ours_body_fill, "600"),
        ]
    )

    parts.append(svg_text(78, 736, "Static baseline single-request run used the low-memory 2x0.5B config to avoid KV-cache startup stalls on the shared GPU.", 15, "#4b5563", "400"))
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    summary = build_summary()
    SUMMARY_JSON_PATH.write_text(json.dumps(
        summary, indent=2) + "\n", encoding="utf-8")
    SUMMARY_MD_PATH.write_text(build_markdown(summary), encoding="utf-8")
    SUMMARY_SVG_PATH.write_text(build_svg(summary), encoding="utf-8")
    print(f"Wrote {SUMMARY_JSON_PATH}")
    print(f"Wrote {SUMMARY_MD_PATH}")
    print(f"Wrote {SUMMARY_SVG_PATH}")


if __name__ == "__main__":
    main()
