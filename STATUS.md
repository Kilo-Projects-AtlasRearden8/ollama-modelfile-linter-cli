# STATUS

## What was built

`modelfile-lint` — a local-first, dependency-free Python CLI that lints Ollama
Modelfiles for best practices: valid instructions, parameter ranges, and
readable formatting, with suggested (auto-applicable) fixes.

Project layout:

```
ollama-modelfile-linter-cli/
├── LICENSE                          # MIT, Copyright (c) 2026 Asdale Dynamics, LLC
├── README.md                        # usage, rules table, credits
├── STATUS.md                        # this file
├── pyproject.toml                   # packaging + console script entry point
├── modelfile_lint/
│   ├── __init__.py                  # version
│   ├── cli.py                       # argparse CLI (text/json, --fix, --min-severity, stdin)
│   ├── fix.py                       # apply suggested fixes in place
│   ├── lint.py                      # Modelfile parser + lint rules
│   └── models.py                    # Finding, Instruction, Modelfile data models
└── tests/
    ├── __init__.py
    └── test_lint.py                 # 24 unit tests (parser, rules, fixer, CLI)
```

Lint rules:

| Code | Severity | Check |
|------|----------|-------|
| MOD001 | error | Missing required `FROM` instruction |
| MOD002 | warning | Unknown instruction |
| MOD003 | warning/error | Parameter out of range or not a number |
| MOD004 | info | Duplicate parameter (last value wins) |
| MOD005 | suggestion | Instruction should be uppercase |
| MOD006 | suggestion | File does not end with a newline |
| MOD007 | warning | `FROM` appears more than once |

Parameter ranges enforced: `temperature` 0–2, `top_p` 0–1, `top_k` >= 0,
`repeat_penalty` >= 0, `num_ctx` >= 0, `num_predict` -1 or >= 0, `num_gpu` >= 0,
`num_thread` >= 0, `mirostat` {0,1,2}, `mirostat_eta` > 0, `mirostat_tau` >= 0,
`num_keep` >= 0, `num_seq` >= 1, `tfs_z` >= 0, `typical_p` > 0,
`presence_penalty` -2–2, `frequency_penalty` -2–2.

Exit status: `1` when any `error`-severity finding remains, otherwise `0`.
No network access, no API keys, no secrets — all checks run locally.

## How to run

From the project folder (no install required):

```bash
python3 -m modelfile_lint.cli [FILE]...
python3 -m modelfile_lint.cli < Modelfile
cat Modelfile | python3 -m modelfile_lint.cli
```

Or install the console script:

```bash
pip install .          # (use --break-system-packages on PEP 668 systems)
modelfile-lint [FILE]...
```

Common flags:

```bash
modelfile-lint --format json Modelfile        # machine-readable output
modelfile-lint --min-severity warning Modelfile
modelfile-lint --fix Modelfile                 # apply suggested fixes in place
```

## Verification results

- `python3 -m unittest discover -s tests -v`: **24/24 tests OK** (parser,
  all lint rules including parameter ranges, auto-fix application, CLI exit
  codes, text/JSON output, stdin handling).
- Manual CLI checks:
  - `tests/fixtures/bad.modelfile` → exit 1, reports MOD002/MOD003/MOD004/MOD005/MOD006
  - `tests/fixtures/valid.modelfile` → exit 0, silent
  - `--fix` applies uppercase-instruction and range-clamp fixes; unfixable
    findings (non-numeric values, unknown instructions) are left untouched
  - `--format json` emits valid JSON with file + findings
  - stdin mode works; console-script entry point `modelfile-lint` installs and runs

## Known gaps

- `'''` (single-quote) fenced blocks are not parsed; only `"""` fences are.
- `--fix` only applies findings with a deterministic replacement (uppercase
  instructions, clamped parameter values, trailing newline). Non-numeric
  values and unknown instructions are reported but not auto-fixed.
- Multi-file `--fix` stops at the first unreadable file (unhandled exception).
- No test framework is pinned in `pyproject.toml` (`pytest` listed only under
  `[project.optional-dependencies] dev`); tests run with stdlib `unittest`.
- Packaging install requires `--break-system-packages` on PEP 668-managed
  Python installations (environment limitation, not a code issue).
- No integration with a running Ollama server; this lints files only.

## Credits

Built by Asdale Dynamics, LLC. MIT License — Copyright (c) 2026 Asdale
Dynamics, LLC.
