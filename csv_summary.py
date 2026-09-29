#!/usr/bin/env python3
"""csv-summary - profile a CSV file from the terminal.

Per column: detected type (int / float / date / string), fill rate, numeric
stats (min/max/mean/stddev, population stddev) or top-k values for
categorical columns. Plus row count and duplicate-row count.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import date


def detect_type(values: list[str]) -> str:
    """Detect the narrowest type covering all non-empty values."""
    nonempty = [v for v in values if v != ""]
    if not nonempty:
        return "empty"
    if all(_is_int(v) for v in nonempty):
        return "int"
    if all(_is_float(v) for v in nonempty):
        return "float"
    if all(_is_date(v) for v in nonempty):
        return "date"
    return "string"


def _is_int(v: str) -> bool:
    try:
        int(v)
        return True
    except ValueError:
        return False


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def _is_date(v: str) -> bool:
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _stddev(xs: list[float]) -> float:
    mu = _mean(xs)
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))


def profile(path: str, top: int = 3) -> dict:
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return {"rows": 0, "duplicate_rows": 0, "columns": {}}
        rows = [r for r in reader if any(cell.strip() != "" for cell in r)]

    cols: dict[str, dict] = {}
    for i, name in enumerate(header):
        values = [r[i] if i < len(r) else "" for r in rows]
        ctype = detect_type(values)
        nonempty = [v for v in values if v.strip() != ""]
        info: dict = {
            "type": ctype,
            "fill_rate": round(len(nonempty) / len(rows), 4) if rows else 0.0,
        }
        if ctype in ("int", "float") and nonempty:
            nums = [float(v) for v in nonempty]
            info["min"] = min(nums)
            info["max"] = max(nums)
            info["mean"] = round(_mean(nums), 4)
            info["stddev"] = round(_stddev(nums), 4)
        elif nonempty:
            counter = Counter(nonempty)
            info["unique"] = len(counter)
            info["top"] = counter.most_common(top)
        cols[name] = info

    row_counter = Counter(tuple(r) for r in rows)
    dupes = sum(c - 1 for c in row_counter.values() if c > 1)
    return {"rows": len(rows), "duplicate_rows": dupes, "columns": cols}


def render(report: dict) -> list[str]:
    lines = [f"rows: {report['rows']}   duplicate rows: {report['duplicate_rows']}"]
    for name, info in report["columns"].items():
        head = f"{name} [{info['type']}] fill={info['fill_rate'] * 100:.1f}%"
        if "mean" in info:
            head += (f"  min={info['min']:g} max={info['max']:g}"
                     f" mean={info['mean']:g} stddev={info['stddev']:g}")
        elif "top" in info:
            tops = ", ".join(f"{v}({c})" for v, c in info["top"])
            head += f"  unique={info['unique']}  top: {tops}"
        lines.append(head)
    return lines


def _selftest() -> int:
    import os
    import tempfile

    failed = 0

    def check(cond: bool, label: str) -> None:
        nonlocal failed
        print(("PASS " if cond else "FAIL ") + label)
        if not cond:
            failed += 1

    fixture = """name,age,city,joined
Alice,34,NYC,2021-01-05
Bob,29,LA,2020-07-30
Carol,,NYC,2022-03-15
Dave,41,LA,2021-01-05
Alice,34,NYC,2021-01-05
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "f.csv")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fixture)

        rep = profile(path)
        check(rep["rows"] == 5, f"row count (got {rep['rows']})")
        check(rep["duplicate_rows"] == 1, f"duplicate rows (got {rep['duplicate_rows']})")

        age = rep["columns"]["age"]
        check(age["type"] == "int", f"age type (got {age['type']})")
        check(age["fill_rate"] == 0.8, f"age fill rate (got {age['fill_rate']})")
        check(age["min"] == 29 and age["max"] == 41, "age min/max")
        check(abs(age["mean"] - 34.5) < 1e-9, f"age mean (got {age['mean']})")
        # population stddev of [34,29,41,34]
        import math as _m
        want = _m.sqrt(((34 - 34.5) ** 2 + (29 - 34.5) ** 2 +
                        (41 - 34.5) ** 2 + (34 - 34.5) ** 2) / 4)
        check(abs(age["stddev"] - round(want, 4)) < 1e-9,
              f"age stddev (got {age['stddev']}, want {round(want, 4)})")

        city = rep["columns"]["city"]
        check(city["type"] == "string", "city type")
        check(city["top"][0] == ("LA", 2) or city["top"][0] == ("NYC", 3),
              f"city top (got {city['top']})")
        check(city["top"][0][1] == 3 and city["top"][0][0] == "NYC",
              f"city top is NYC(3) (got {city['top']})")

        joined = rep["columns"]["joined"]
        check(joined["type"] == "date", f"joined type (got {joined['type']})")
        check(joined["top"][0] == ("2021-01-05", 3), "joined top value")

        name_c = rep["columns"]["name"]
        check(name_c["fill_rate"] == 1.0, "name fill complete")

        lines = render(rep)
        check(any("duplicate rows: 1" in ln for ln in lines), "render shows dupes")
        check(any("[date]" in ln for ln in lines), "render shows date type")

    print(f"selftest: failures={failed}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--test" in argv:
        return _selftest()

    ap = argparse.ArgumentParser(
        prog="csv-summary", description="Profile a CSV file from the terminal.")
    ap.add_argument("file", help="CSV file to profile")
    ap.add_argument("--top", type=int, default=3,
                    help="top-k values for categorical columns")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        report = profile(args.file, top=args.top)
    except (OSError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("\n".join(render(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
