# modelfile-lint

A friendly, local-first command-line tool that checks your Ollama Modelfiles
for best practices — valid instructions, sensible parameter ranges, and clean
formatting — and offers suggested fixes you can apply automatically.

Built and maintained by [Asdale Dynamics, LLC](https://dylanasdale.github.io).

## Who this is for

If you're running Ollama locally and writing Modelfiles by hand, this tool is
for you. It catches common mistakes (a lowercase `from`, a `temperature` set
higher than 2, a missing `FROM` line, a file without a trailing newline) before
they cause confusing behavior. No account, no API key, no internet connection
needed — everything runs right on your own computer.

## What it checks

| Code | Severity | What it means |
|------|----------|---------------|
| MOD001 | error | Your Modelfile is missing the required `FROM` instruction. |
| MOD002 | warning | An instruction isn't one Ollama recognizes. |
| MOD003 | warning/error | A `PARAMETER` value is out of range, or not a number. |
| MOD004 | info | The same parameter appears more than once (the last value wins). |
| MOD005 | suggestion | An instruction should be uppercase (e.g. `from` → `FROM`). |
| MOD006 | suggestion | The file doesn't end with a newline. |
| MOD007 | warning | `FROM` appears more than once (only the first is used). |

Parameter ranges checked:

- `temperature`: 0 to 2
- `top_p`: 0 to 1
- `top_k`: 0 or higher
- `repeat_penalty`: 0 or higher
- `seed`: any integer
- `num_ctx`: 0 or higher
- `num_predict`: -1 or higher
- `num_gpu`: 0 or higher
- `num_thread`: 0 or higher
- `mirostat`: 0, 1, or 2
- `mirostat_eta`: greater than 0
- `mirostat_tau`: 0 or higher
- `num_keep`: 0 or higher
- `num_seq`: 1 or higher
- `tfs_z`: 0 or higher
- `typical_p`: greater than 0
- `presence_penalty`: -2 to 2
- `frequency_penalty`: -2 to 2

## Install

From this folder:

```bash
pip install .
```

(On some systems you may need `pip install --break-system-packages .`.)

Or run without installing:

```bash
python3 -m modelfile_lint.cli Modelfile
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

JSON output (handy for editors and other tools):

```bash
modelfile-lint --format json Modelfile
```

Report only errors and warnings (hide info and suggestions):

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
Modelfile:1: MOD005 suggestion: Instruction 'from' should be uppercase 'FROM'.  -> FROM llama3
Modelfile:2: MOD003 warning: Parameter 'temperature'=3.0 exceeds maximum 2.0.  -> PARAMETER temperature 2
```

Run `modelfile-lint --fix Modelfile` and the file is rewritten to:

```dockerfile
FROM llama3
PARAMETER temperature 2
```

## Local-first

This tool never contacts the network, never reads or writes API keys, and never
sends your Modelfiles anywhere. All checks happen on your machine.

## License

MIT. Copyright (c) 2026 Asdale Dynamics, LLC. See LICENSE.

## About

Asdale Dynamics, LLC (Indiana, formed October 2026) is the LLC of Dylan
Asdale, a registered nurse turned AI author and founder. The LLC publishes
beginner-friendly AI education, books and guides, and practical open-source
tools — including this linter. Dylan's book *The Massive AI Manual* and hub
site dylanasdale.github.io explain AI "like a friend would": plain English,
step by step, never condescending.
