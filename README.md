# modelfile-lint

Local-first CLI linter for Ollama Modelfiles. Checks parameter ranges,
valid instructions, and readable formatting, and offers suggested fixes.
No keys, no network, no secrets — everything runs on your machine.

Built and maintained by [Asdale Dynamics, LLC](https://dylanasdale.github.io).

## What it checks

| Code | Severity | Check |
|------|----------|-------|
| MOD001 | error | Missing required `FROM` instruction |
| MOD002 | warning | Unknown instruction |
| MOD003 | warning/error | Parameter value outside its valid range (or not a number) |
| MOD004 | info | Duplicate parameter (last value wins) |
| MOD005 | suggestion | Instruction should be uppercase |
| MOD006 | suggestion | File does not end with a newline |
| MOD007 | warning | `FROM` appears more than once |

Supported parameter ranges include `temperature` (0–2), `top_p` (0–1),
`top_k`, `repeat_penalty`, `num_ctx`, `num_predict`, `num_gpu`,
`num_thread`, `mirostat` (0/1/2), `mirostat_eta`, `mirostat_tau`,
`num_keep`, `num_seq`, `tfs_z`, `typical_p`, `presence_penalty`
(-2–2), and `frequency_penalty` (-2–2).

## Install

```bash
git clone https://github.com/dylanasdale/ollama-modelfile-linter-cli.git
cd ollama-modelfile-linter-cli
pip install .
```

Or run without installing:

```bash
python -m modelfile_lint.cli Modelfile
```

## Usage

Lint one or more Modelfiles:

```bash
modelfile-lint Modelfile
modelfile-lint Modelfile.dev Modelfile.prod
```

Lint from stdin:

```bash
cat Modelfile | modelfile-lint
```

JSON output (useful for editors and CI):

```bash
modelfile-lint --format json Modelfile
```

Report only errors and warnings:

```bash
modelfile-lint --min-severity warning Modelfile
```

Apply suggested fixes in place:

```bash
modelfile-lint --fix Modelfile
```

Exit status is `1` when any `error`-severity finding remains, otherwise `0`.

## Example

Given a `Modelfile`:

```dockerfile
from llama3
PARAMETER temperature 3.0
```

Running `modelfile-lint Modelfile` reports:

```
Modelfile:1: MOD005 suggestion: Instruction 'from' should be uppercase 'FROM'.  -> FROM
Modelfile:2: MOD003 warning: Parameter 'temperature'=3.0 exceeds maximum 2.0.  -> PARAMETER temperature 2
```

Run `modelfile-lint --fix Modelfile` to apply the suggested replacements.

## Local-first

This tool never contacts the network, never reads or writes API keys, and
never sends your Modelfiles anywhere. All checks happen locally.

## License

MIT. Copyright (c) 2026 Asdale Dynamics, LLC. See LICENSE.

## About

Asdale Dynamics, LLC (Indiana, formed October 2026) is the LLC of Dylan
Asdale, a registered nurse turned AI author and founder. The LLC publishes
beginner-friendly AI education, books and guides, and practical open-source
tools — including this linter. Dylan's book *The Massive AI Manual* and hub
site dylanasdale.github.io explain AI "like a friend would": plain English,
step by step, never condescending.
