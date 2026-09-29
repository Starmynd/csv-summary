# csv-summary

Profile CSV files from the terminal: column types, fill rates, numeric stats,
top values and duplicate rows. One file, standard library only - no pandas
required for a quick look at a file.

## Features

- Automatic per-column type detection: `int`, `float`, `date` (ISO), `string`
- Fill rate per column
- Numeric columns: min, max, mean, stddev (population)
- Categorical columns: unique count and top-k values
- Row count and duplicate-row count
- Human table or `--json` output

## Usage

```console
$ csv-summary data.csv
rows: 5   duplicate rows: 1
name [string] fill=100.0%  unique=4  top: Alice(2), Bob(1), Carol(1)
age [int] fill=80.0%  min=29 max=41 mean=34.5 stddev=4.272
city [string] fill=100.0%  unique=2  top: NYC(3), LA(2)
joined [date] fill=100.0%  unique=3  top: 2021-01-05(3), 2020-07-30(1), 2022-03-15(1)

$ csv-summary data.csv --json | jq .columns.age
$ csv-summary data.csv --top 5

$ python3 csv_summary.py --test
selftest: failures=0
```

## Notes

- Empty lines and fully-empty rows are ignored.
- Type detection is per column over all non-empty values; a single
  non-numeric value downgrades the column to `string`.
- Dates must be ISO `YYYY-MM-DD`.

## Testing

```console
$ python3 csv_summary.py --test
```

Asserts exact row/duplicate counts, type detection, fill rates, min/max/
mean/stddev on a known fixture and top-value ordering.

## License

MIT
