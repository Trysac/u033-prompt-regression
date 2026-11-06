"""Tests for the public API and the command line of prompt_regression."""

from __future__ import annotations

import json
import logging
import runpy
import sys
from pathlib import Path
from typing import Any

import pytest

import prompt_regression
from prompt_regression import (
    CaseDiff,
    Normalizer,
    RegressionError,
    RunRecord,
    compare,
    load_run,
    render,
)
from prompt_regression.__main__ import main

LONG_OUTPUT = "x" * 100_001
GOOD_LINE = '{"id":"a","output":"x"}'


def rec(case_id: str, output: str, score: float | None = None) -> RunRecord:
    return RunRecord(case_id, output, score)


def run_of(*records: RunRecord) -> dict[str, RunRecord]:
    return {r.case_id: r for r in records}


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def setup_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    before: list[dict[str, object]],
    after: list[dict[str, object]],
) -> None:
    monkeypatch.chdir(tmp_path)
    write_jsonl(tmp_path / "before.jsonl", before)
    write_jsonl(tmp_path / "after.jsonl", after)


def status_of(before: str, after: str, normalizer: Normalizer | None = None) -> str:
    norm = normalizer or Normalizer()
    return compare(run_of(rec("c", before)), run_of(rec("c", after)), norm)[0].status


def padded_line(size: int) -> str:
    line = '{"id":"a","output":"' + "x" * (size - 22) + '"}'
    assert len(line) == size
    return line


def test_version_and_null_handler() -> None:
    assert prompt_regression.__version__ == "0.1.0"
    handlers = logging.getLogger("prompt_regression").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)


def test_regression_error_fields_and_clipping() -> None:
    err = RegressionError("input_invalid", "x" * 500)
    assert err.code == "input_invalid"
    assert err.path is None and err.line is None
    assert len(str(err)) == 200 and str(err).endswith("...")
    short = RegressionError("duplicate_case_id", "dup", "f.jsonl", 4)
    assert (short.path, short.line, str(short)) == ("f.jsonl", 4, "dup")


def test_compare_covers_union_sorted_by_id() -> None:
    before = run_of(rec("b", "gone"), rec("a", "same"), rec("d", "old"))
    after = run_of(rec("a", "same"), rec("c", "new"), rec("d", "new"))
    diffs = compare(before, after)
    assert [(d.case_id, d.status) for d in diffs] == [
        ("a", "unchanged"),
        ("b", "removed"),
        ("c", "added"),
        ("d", "changed"),
    ]
    unchanged, removed, added, changed = diffs
    assert unchanged.diff == ()
    assert removed.before == "gone" and removed.after is None
    assert removed.diff[0] == "--- before" and removed.diff[-1] == "-gone"
    assert added.before is None and added.after == "new"
    assert added.diff[0] == "--- before" and added.diff[-1] == "+new"
    assert changed.diff[-2:] == ("-old", "+new")
    assert changed.score_delta is None


def test_compare_empty_runs() -> None:
    assert compare({}, {}) == []


def test_json_canonical_examples() -> None:
    norm = Normalizer(strip=True, casefold=True, json_canonical=True)
    assert norm.apply(' {"b":1,"a":2}') == '{"a":2,"b":1}'
    assert status_of('{"a": 2, "b": 1}', ' {"b":1,"a":2}', norm) == "unchanged"
    assert status_of("1", "1.0", norm) == "changed"
    assert status_of("0.0", "-0.0", norm) == "changed"
    text_norm = Normalizer(json_canonical=True)
    assert text_norm.apply('{"a":1} ok') == '{"a":1} ok'
    assert status_of('{"a":1} ok', '{"a": 1} ok', text_norm) == "changed"


def test_json_canonical_int_versus_float_literals() -> None:
    norm = Normalizer(strip=True, casefold=True, json_canonical=True)
    # '1' versus '1.0' is 'changed' (int versus float)
    assert status_of("1", "1.0", norm) == "changed"


def test_normalizer_whitespace_and_case() -> None:
    assert Normalizer().apply("a  \r\nb \r\n\r\n") == "a\nb"
    assert Normalizer(strip=False).apply("a \r\nb ") == "a \nb "
    assert Normalizer(casefold=True).apply("Stra\u00dfe") == "strasse"
    assert Normalizer().apply("  Keep Case  ") == "Keep Case"


def test_normalizer_json_edge_cases() -> None:
    norm = Normalizer(json_canonical=True)
    assert norm.apply("NaN") == "NaN"
    assert norm.apply('{"k":"caf\u00e9"}') == '{"k":"caf\u00e9"}'
    assert norm.apply("[1, 2]") == "[1,2]"
    assert norm.apply("") == ""
    deep = "[" * 100_000 + "]" * 100_000
    assert norm.apply(deep) == deep


def test_normalizer_rejects_oversized_text() -> None:
    with pytest.raises(RegressionError) as excinfo:
        Normalizer().apply("x" * 10_000_001)
    assert excinfo.value.code == "input_too_large"


def test_score_statuses() -> None:
    lower = rec("c", "a", 0.5)
    higher = rec("c", "b", 0.75)
    better = compare(run_of(lower), run_of(higher), tolerance=0.2)[0]
    assert better.status == "improved"
    assert better.score_delta == 0.25
    worse = compare(run_of(higher), run_of(lower), tolerance=0.2)[0]
    assert worse.status == "regressed"
    assert worse.score_delta == -0.25
    assert compare(run_of(lower), run_of(higher), tolerance=0.25)[0].status == "changed"
    assert compare(run_of(higher), run_of(lower), tolerance=0.25)[0].status == "changed"
    assert compare(run_of(lower), run_of(higher))[0].status == "improved"


def test_score_in_one_run_only_is_changed() -> None:
    first = compare(run_of(rec("c", "a", 0.5)), run_of(rec("c", "b")))[0]
    assert first.status == "changed" and first.score_delta is None
    second = compare(run_of(rec("c", "a")), run_of(rec("c", "b", 0.5)))[0]
    assert second.status == "changed" and second.score_delta is None


def test_equal_outputs_are_unchanged_despite_scores() -> None:
    result = compare(run_of(rec("c", "same", 0.1)), run_of(rec("c", " same ", 0.9)))[0]
    assert result.status == "unchanged"
    assert result.score_delta is None


@pytest.mark.parametrize("tolerance", [-1.0, float("nan"), float("inf")])
def test_compare_rejects_bad_tolerance(tolerance: float) -> None:
    with pytest.raises(RegressionError) as excinfo:
        compare({}, {}, tolerance=tolerance)
    assert excinfo.value.code == "input_invalid"


def test_markdown_header_and_escaping() -> None:
    diffs = compare(run_of(rec("a|<b>", "x")), run_of(rec("a|<b>", "y")))
    report = render(diffs, "markdown")
    start = "## Prompt regression\n\n| status | count |\n| --- | --- |\n| unchanged | "
    assert report.startswith(start)
    assert "<details><summary>a\\|&lt;b&gt; (changed)</summary>" in report


def test_markdown_escapes_other_markup() -> None:
    assert "<summary>a&amp;b (changed)</summary>" in render(
        compare(run_of(rec("a&b", "x")), run_of(rec("a&b", "y"))), "markdown"
    )
    report = render(
        compare(run_of(rec("</details>", "x")), run_of(rec("</details>", "y"))), "markdown"
    )
    assert "<summary>&lt;/details&gt; (changed)</summary>" in report
    lines = render(
        compare(run_of(rec("a\n# h", "x")), run_of(rec("a\n# h", "y"))), "markdown"
    ).split("\n")
    assert "<details><summary>a # h (changed)</summary>" in lines


def test_markdown_counts_all_statuses_in_order() -> None:
    before = run_of(
        rec("u", "same"),
        rec("c", "old"),
        rec("i", "old", 0.1),
        rec("r", "old", 0.9),
        rec("d", "gone"),
    )
    after = run_of(
        rec("u", "same"),
        rec("c", "new"),
        rec("i", "new", 0.5),
        rec("r", "new", 0.2),
        rec("a", "fresh"),
    )
    lines = render(compare(before, after), "markdown").split("\n")
    assert lines[4:10] == [
        "| unchanged | 1 |",
        "| changed | 1 |",
        "| improved | 1 |",
        "| regressed | 1 |",
        "| added | 1 |",
        "| removed | 1 |",
    ]
    summaries = [line for line in lines if line.startswith("<details>")]
    assert summaries == [
        "<details><summary>a (added)</summary>",
        "<details><summary>c (changed)</summary>",
        "<details><summary>d (removed)</summary>",
        "<details><summary>i (improved)</summary>",
        "<details><summary>r (regressed)</summary>",
    ]


def test_fence_grows_past_backtick_runs() -> None:
    diffs = compare(run_of(rec("a", "x")), run_of(rec("a", "```\n</details>")))
    lines = render(diffs, "markdown").split("\n")
    assert "````diff" in lines
    assert "```diff" not in lines
    assert lines[-2:] == ["````", "</details>"]
    four = CaseDiff("a", "changed", "x", "````", None, ("+````",))
    assert "`````diff" in render([four], "markdown").split("\n")
    plain = CaseDiff("a", "changed", "x", "y", None, ("+y",))
    assert "```diff" in render([plain], "markdown").split("\n")


def test_diff_truncation() -> None:
    diff = tuple(f"+l{i}" for i in range(10))
    item = CaseDiff("a", "changed", "x", "y", None, diff)
    report = render([item], "markdown", max_diff_lines=3)
    assert "```diff\n+l0\n+l1\n+l2\n... 7 more lines\n```\n</details>" in report
    assert "+l3" not in report
    assert "... 10 more lines" in render([item], "markdown", max_diff_lines=0)
    assert "more lines" not in render([item], "markdown", max_diff_lines=10)


def test_long_outputs_omit_the_diff() -> None:
    result = compare(run_of(rec("a", "short")), run_of(rec("a", LONG_OUTPUT)))[0]
    assert result.status == "changed"
    assert result.diff == ("diff omitted: output too long",)
    reverse = compare(run_of(rec("a", LONG_OUTPUT)), run_of(rec("a", "short")))[0]
    assert reverse.diff == ("diff omitted: output too long",)
    removed = compare(run_of(rec("a", LONG_OUTPUT)), {})[0]
    assert removed.status == "removed"
    assert removed.diff == ("diff omitted: output too long",)
    exact = compare(run_of(rec("a", "short")), run_of(rec("a", "x" * 100_000)))[0]
    assert exact.diff[0] == "--- before"


def test_render_json() -> None:
    before = run_of(rec("a", "x", 0.5), rec("b", "k"))
    after = run_of(rec("a", "y", 0.75), rec("c", "n"))
    text = render(compare(before, after), "json")
    data = json.loads(text)
    assert [item["case_id"] for item in data] == ["a", "b", "c"]
    assert data[0]["status"] == "improved"
    assert data[0]["score_delta"] == 0.25
    assert isinstance(data[0]["diff"], list)
    assert data[1]["after"] is None
    assert text == json.dumps(data, sort_keys=True, indent=2)
    assert render([], "json") == "[]"


def test_render_empty_markdown() -> None:
    report = render([], "markdown")
    assert "<details>" not in report
    for status in ("unchanged", "changed", "improved", "regressed", "added", "removed"):
        assert f"| {status} | 0 |" in report


def test_render_rejects_bad_arguments() -> None:
    bad_format: Any = "html"
    with pytest.raises(RegressionError) as excinfo:
        render([], bad_format)
    assert excinfo.value.code == "input_invalid"
    with pytest.raises(RegressionError) as excinfo2:
        render([], "markdown", max_diff_lines=-1)
    assert excinfo2.value.code == "input_invalid"


def test_load_run_reads_records(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        '\n{"id":"a","output":"caf\u00e9 \u2713","score":1}\n   \n'
        '{"id":"b","output":"y","score":0.5}\r\n{"id":"c","output":"z","score":null}\n'
        '{"id":"d","output":"w"}',
        encoding="utf-8",
    )
    result = load_run(path)
    assert list(result) == ["a", "b", "c", "d"]
    assert result["a"] == RunRecord("a", "caf\u00e9 \u2713", 1.0)
    assert isinstance(result["a"].score, float)
    assert result["b"].score == 0.5
    assert result["c"].score is None and result["d"].score is None


def test_load_run_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    assert load_run(path) == {}


@pytest.mark.parametrize(
    "line",
    [
        "[]",
        "1",
        '"s"',
        "{}",
        '{"id":1,"output":"x"}',
        '{"id":"a"}',
        '{"id":"a","output":2}',
        "{bad",
        "nul",
    ],
)
def test_load_run_rejects_invalid_lines(tmp_path: Path, line: str) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(GOOD_LINE.replace('"a"', '"z"') + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    err = excinfo.value
    assert err.code == "input_invalid"
    assert err.path == str(path) and err.line == 2
    assert len(str(err)) <= 200


def test_load_run_rejects_deeply_nested_line(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text("[" * 100_000 + "\n", encoding="utf-8")
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    assert excinfo.value.code == "input_invalid" and excinfo.value.line == 1


def test_load_run_line_numbers_count_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text("\n\n{oops\n", encoding="utf-8")
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    assert excinfo.value.line == 3


@pytest.mark.parametrize(
    "score_text", ["NaN", "true", '"1"', "Infinity", "-Infinity", "1e999", "[1]", "false"]
)
def test_load_run_rejects_bad_scores(tmp_path: Path, score_text: str) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        GOOD_LINE + '\n{"id":"b","output":"y","score":' + score_text + "}\n", encoding="utf-8"
    )
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    err = excinfo.value
    assert err.code == "input_invalid"
    assert err.path == str(path) and err.line == 2


def test_load_run_rejects_huge_integer_score(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text('{"id":"a","output":"x","score":1' + "0" * 400 + "}\n", encoding="utf-8")
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    assert excinfo.value.code == "input_invalid" and excinfo.value.line == 1


def test_load_run_rejects_bad_bytes(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_bytes(b'{"id":"a","output":"\xff"}\n')
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    assert excinfo.value.code == "input_invalid" and excinfo.value.line == 1
    path.write_bytes(b'{"id":"\\ud800","output":"x"}\n')
    with pytest.raises(RegressionError) as excinfo2:
        load_run(path)
    assert excinfo2.value.code == "input_invalid" and excinfo2.value.line == 1
    path.write_bytes(b'{"id":"a","output":"\\udfff"}\n')
    with pytest.raises(RegressionError) as excinfo3:
        load_run(path)
    assert excinfo3.value.code == "input_invalid"


def test_load_run_duplicate_id(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    write_jsonl(path, [{"id": "dup", "output": "x"}, {"id": "dup", "output": "y"}])
    with pytest.raises(RegressionError) as excinfo:
        load_run(path)
    err = excinfo.value
    assert err.code == "duplicate_case_id"
    assert err.path == str(path) and err.line == 2
    long_id = "x" * 1000
    write_jsonl(path, [{"id": long_id, "output": "x"}, {"id": long_id, "output": "y"}])
    with pytest.raises(RegressionError) as excinfo2:
        load_run(path)
    assert len(str(excinfo2.value)) <= 200


def test_load_run_file_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_bytes(b"x" * 11)
    with pytest.raises(RegressionError) as excinfo:
        load_run(path, max_bytes=10)
    assert excinfo.value.code == "input_too_large"
    assert excinfo.value.path == str(path)
    path.write_bytes((GOOD_LINE + "\n").encode("utf-8"))
    size = len(GOOD_LINE) + 1
    assert list(load_run(path, max_bytes=size)) == ["a"]
    with pytest.raises(RegressionError) as excinfo2:
        load_run(path, max_bytes=size - 1)
    assert excinfo2.value.code == "input_too_large"


def test_load_run_line_size_limit(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(padded_line(50) + "\n", encoding="utf-8")
    assert list(load_run(path, max_line_bytes=50)) == ["a"]
    path.write_bytes((padded_line(50) + "\r\n").encode())
    assert list(load_run(path, max_line_bytes=50)) == ["a"]
    for text in (padded_line(51) + "\n", padded_line(51), padded_line(500) + "\n"):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(RegressionError) as excinfo:
            load_run(path, max_line_bytes=50)
        assert excinfo.value.code == "input_too_large"
        assert excinfo.value.path == str(path) and excinfo.value.line == 1


def test_load_run_unreadable_paths(tmp_path: Path) -> None:
    with pytest.raises(RegressionError) as excinfo:
        load_run(tmp_path / "missing.jsonl")
    assert excinfo.value.code == "input_invalid" and excinfo.value.line is None
    with pytest.raises(RegressionError) as excinfo2:
        load_run(tmp_path)
    assert excinfo2.value.code == "input_invalid"
    with pytest.raises(RegressionError) as excinfo3:
        load_run(tmp_path / "x.jsonl", max_bytes=-1)
    assert excinfo3.value.code == "input_invalid"


def test_unicode_round_trip(tmp_path: Path) -> None:
    word = "caf\u00e9 \u2713"
    before = write_jsonl(tmp_path / "b.jsonl", [{"id": "\u00e9", "output": word}])
    after = write_jsonl(tmp_path / "a.jsonl", [{"id": "\u00e9", "output": word + "!"}])
    diffs = compare(load_run(before), load_run(after))
    assert diffs[0].status == "changed"
    assert "+" + word + "!" in diffs[0].diff


def test_cli_fail_on_regressed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["before.jsonl", "after.jsonl", "--fail-on", "regressed"]
    setup_cli(
        tmp_path,
        monkeypatch,
        [{"id": "a", "output": "x", "score": 0.9}],
        [{"id": "a", "output": "y", "score": 0.1}],
    )
    assert main(args) == 1
    assert "| regressed | 1 |" in capsys.readouterr().out
    setup_cli(
        tmp_path,
        monkeypatch,
        [{"id": "a", "output": "x", "score": 0.1}],
        [{"id": "a", "output": "y", "score": 0.9}],
    )
    assert main(args) == 0


def test_cli_fail_on_changed_and_never(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_cli(
        tmp_path,
        monkeypatch,
        [{"id": "a", "output": "x"}],
        [{"id": "a", "output": "x"}, {"id": "b", "output": "y"}],
    )
    base = ["before.jsonl", "after.jsonl"]
    assert main([*base, "--fail-on", "changed"]) == 1
    assert main([*base, "--fail-on", "regressed"]) == 0
    assert main([*base, "--fail-on", "never"]) == 0
    assert main(base) == 0


def test_cli_invalid_json_reports_path_and_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_cli(tmp_path, monkeypatch, [], [{"id": "a", "output": "x"}])
    (tmp_path / "before.jsonl").write_text(
        '{"id":"a","output":"x"}\n{"id":"b","output":"y"}\n{oops\n', encoding="utf-8"
    )
    assert main(["before.jsonl", "after.jsonl"]) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("before.jsonl:3: ")
    assert captured.out == ""


def test_cli_duplicate_and_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rows: list[dict[str, object]] = [{"id": "a", "output": "x"}, {"id": "a", "output": "y"}]
    setup_cli(tmp_path, monkeypatch, rows, [])
    assert main(["before.jsonl", "after.jsonl"]) == 2
    assert capsys.readouterr().err.startswith("before.jsonl:2: ")
    assert main(["missing.jsonl", "after.jsonl"]) == 2
    assert capsys.readouterr().err.startswith("missing.jsonl: ")


def test_cli_usage_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_cli(tmp_path, monkeypatch, [], [])
    base = ["before.jsonl", "after.jsonl"]
    assert main([*base, "--tolerance", "-1"]) == 2
    assert capsys.readouterr().err.startswith("prompt-regression: ")
    assert main([*base, "--tolerance", "nan"]) == 2
    assert main([*base, "--tolerance", "abc"]) == 2
    assert main([*base, "--max-diff-lines", "-1"]) == 2
    assert main([*base, "--format", "xml"]) == 2
    assert main([*base, "--fail-on", "sometimes"]) == 2
    assert main(["only-one.jsonl"]) == 2
    assert main(["--help"]) == 0


def test_cli_json_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_cli(tmp_path, monkeypatch, [{"id": "a", "output": "x"}], [{"id": "a", "output": "y"}])
    assert main(["before.jsonl", "after.jsonl", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [item["status"] for item in data] == ["changed"]


def test_cli_normalisation_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = ["before.jsonl", "after.jsonl", "--fail-on", "changed"]
    setup_cli(
        tmp_path, monkeypatch, [{"id": "a", "output": "Hello"}], [{"id": "a", "output": "hello"}]
    )
    assert main(base) == 1
    assert main([*base, "--casefold"]) == 0
    first = {"id": "a", "output": '{"a":1,"b":2}'}
    second = {"id": "a", "output": '{"b":2,"a":1}'}
    setup_cli(tmp_path, monkeypatch, [first], [second])
    assert main(base) == 1
    assert main([*base, "--json-canonical"]) == 0
    setup_cli(tmp_path, monkeypatch, [{"id": "a", "output": "a"}], [{"id": "a", "output": "a "}])
    assert main(base) == 0
    assert main([*base, "--no-strip"]) == 1


def test_cli_tolerance_and_diff_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_cli(
        tmp_path,
        monkeypatch,
        [{"id": "a", "output": "a\nb\nc\nd", "score": 0.5}],
        [{"id": "a", "output": "A\nB\nC\nD", "score": 0.75}],
    )
    base = ["before.jsonl", "after.jsonl", "--fail-on", "regressed"]
    assert main([*base, "--max-diff-lines", "1", "--tolerance", "0.2"]) == 0
    out = capsys.readouterr().out
    assert "... 10 more lines" in out
    assert "| improved | 1 |" in out
    assert main([*base, "--tolerance", "0.25"]) == 0
    assert "| changed | 1 |" in capsys.readouterr().out


def test_cli_empty_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "before.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "after.jsonl").write_text("", encoding="utf-8")
    assert main(["before.jsonl", "after.jsonl", "--fail-on", "changed"]) == 0
    out = capsys.readouterr().out
    assert "| unchanged | 0 |" in out and "| removed | 0 |" in out


def test_cli_default_argv_and_module_entry_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_cli(tmp_path, monkeypatch, [{"id": "a", "output": "x"}], [{"id": "a", "output": "x"}])
    monkeypatch.setattr(sys, "argv", ["prompt-regression", "before.jsonl", "after.jsonl"])
    assert main() == 0
    assert "## Prompt regression" in capsys.readouterr().out
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("prompt_regression.__main__", run_name="__main__")
    assert excinfo.value.code == 0
