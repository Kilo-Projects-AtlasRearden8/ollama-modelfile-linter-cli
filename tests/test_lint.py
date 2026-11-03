"""Unit tests for the modelfile-lint core logic."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest

from modelfile_lint.cli import main
from modelfile_lint.fix import apply_fixes
from modelfile_lint.lint import lint, parse

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as handle:
        return handle.read()


class ParseTests(unittest.TestCase):
    def test_parses_instructions_and_blocks(self):
        mf = parse(read_fixture("valid.modelfile"), "tests/fixtures/valid.modelfile")
        keywords = [inst.keyword for inst in mf.instructions]
        self.assertIn("FROM", keywords)
        self.assertIn("PARAMETER", keywords)
        self.assertIn("TEMPLATE", keywords)
        self.assertIn("SYSTEM", keywords)
        self.assertIn("MESSAGE", keywords)
        template = next(i for i in mf.instructions if i.keyword == "TEMPLATE")
        self.assertIsNotNone(template.block)
        self.assertIn("{{ .Prompt }}", template.block)

    def test_skips_comments_and_blank_lines(self):
        mf = parse("# comment\n\nFROM llama3\n", "x")
        self.assertEqual(len(mf.instructions), 1)
        self.assertEqual(mf.instructions[0].keyword, "FROM")

    def test_parses_multi_line_template_block(self):
        text = 'FROM llama3\nTEMPLATE """Hello {{ .Name }}!\nThis is line two."""\n'
        mf = parse(text, "x")
        template = next(i for i in mf.instructions if i.keyword == "TEMPLATE")
        self.assertIsNotNone(template.block)
        self.assertIn("Hello {{ .Name }}!", template.block)
        self.assertIn("This is line two.", template.block)

    def test_parses_single_quote_fenced_block(self):
        text = "FROM llama3\nSYSTEM '''You are helpful.'''\n"
        mf = parse(text, "x")
        system = next(i for i in mf.instructions if i.keyword == "SYSTEM")
        self.assertEqual(system.block, "You are helpful.")


class LintTests(unittest.TestCase):
    def findings(self, text: str, path: str = "<test>"):
        return lint(parse(text, path))

    def test_valid_modelfile_no_findings(self):
        findings = self.findings(
            read_fixture("valid.modelfile"), "tests/fixtures/valid.modelfile"
        )
        self.assertEqual(findings, [])

    def test_missing_from_is_error(self):
        findings = self.findings("PARAMETER temperature 0.7\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "MOD001")
        self.assertEqual(findings[0].severity, "error")

    def test_unknown_instruction_warning(self):
        findings = self.findings("FROM llama3\nFOO bar\n")
        codes = [(f.code, f.severity) for f in findings]
        self.assertIn(("MOD002", "warning"), codes)

    def test_temperature_above_max(self):
        findings = self.findings("FROM llama3\nPARAMETER temperature 3.0\n")
        f = findings[0]
        self.assertEqual(f.code, "MOD003")
        self.assertEqual(f.severity, "warning")
        self.assertIsNotNone(f.replacement)
        self.assertIn("2", f.replacement)

    def test_temperature_below_min(self):
        findings = self.findings("FROM llama3\nPARAMETER temperature -1.0\n")
        f = findings[0]
        self.assertEqual(f.code, "MOD003")
        self.assertIsNotNone(f.replacement)

    def test_top_p_above_max(self):
        findings = self.findings("FROM llama3\nPARAMETER top_p 1.5\n")
        self.assertEqual(findings[0].code, "MOD003")

    def test_num_predict_below_min(self):
        findings = self.findings("FROM llama3\nPARAMETER num_predict -5\n")
        self.assertEqual(findings[0].code, "MOD003")

    def test_mirostat_outside_allowed(self):
        findings = self.findings("FROM llama3\nPARAMETER mirostat 5\n")
        self.assertEqual(findings[0].code, "MOD003")

    def test_mirostat_valid_values(self):
        for value in (0, 1, 2):
            findings = self.findings(f"FROM llama3\nPARAMETER mirostat {value}\n")
            self.assertEqual(findings, [], f"mirostat {value} should be valid")

    def test_duplicate_parameter_info(self):
        findings = self.findings(
            "FROM llama3\nPARAMETER temperature 0.5\nPARAMETER temperature 0.9\n"
        )
        codes = [f.code for f in findings]
        self.assertIn("MOD004", codes)
        self.assertEqual(findings[codes.index("MOD004")].severity, "info")

    def test_lowercase_instruction_suggestion(self):
        findings = self.findings("from llama3\n")
        self.assertEqual(findings[0].code, "MOD005")
        self.assertEqual(findings[0].severity, "suggestion")
        self.assertEqual(findings[0].replacement, "FROM llama3")

    def test_non_numeric_parameter_error(self):
        findings = self.findings("FROM llama3\nPARAMETER seed notanumber\n")
        self.assertEqual(findings[0].code, "MOD003")
        self.assertEqual(findings[0].severity, "error")

    def test_missing_trailing_newline_suggestion(self):
        findings = self.findings("FROM llama3\nPARAMETER temperature 0.7")
        self.assertTrue(any(f.code == "MOD006" for f in findings))

    def test_fixture_bad_modelfile(self):
        findings = self.findings(
            read_fixture("bad.modelfile"), "tests/fixtures/bad.modelfile"
        )
        codes = [f.code for f in findings]
        self.assertIn("MOD005", codes)  # lowercase from
        self.assertIn("MOD003", codes)  # range + non-numeric
        self.assertIn("MOD004", codes)  # duplicate temperature
        self.assertIn("MOD002", codes)  # unknown instruction
        errors = [f for f in findings if f.severity == "error"]
        self.assertTrue(any("not a number" in f.message for f in errors))


class FixTests(unittest.TestCase):
    def test_applies_fixes_bottom_up(self):
        text = "from llama3\nPARAMETER temperature 3.0\n"
        findings = lint(parse(text, "x"))
        result, applied = apply_fixes(text, findings)
        self.assertEqual(len(applied), 2)
        self.assertEqual(result.split("\n")[0], "FROM llama3")
        self.assertIn("PARAMETER temperature 2", result.split("\n")[1])

    def test_trailing_newline_fix(self):
        text = "FROM llama3"
        findings = lint(parse(text, "x"))
        result, _ = apply_fixes(text, findings)
        self.assertTrue(result.endswith("\n"))


class CliTests(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        old_stdout, old_stdin = sys.stdout, sys.stdin
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            code = main(list(args))
            output = sys.stdout.getvalue()
            error = sys.stderr.getvalue()
        finally:
            sys.stdout, sys.stderr, sys.stdin = old_stdout, old_stderr, old_stdin
        return code, output, error

    def test_cli_valid_file(self):
        code, output, _ = self.run_cli(os.path.join(FIXTURES, "valid.modelfile"))
        self.assertEqual(code, 0)
        self.assertEqual(output.strip(), "")

    def test_cli_bad_file(self):
        code, output, _ = self.run_cli(os.path.join(FIXTURES, "bad.modelfile"))
        self.assertEqual(code, 1)
        self.assertIn("MOD005", output)
        self.assertIn("MOD003", output)

    def test_cli_json_format(self):
        code, output, _ = self.run_cli(
            "--format", "json", os.path.join(FIXTURES, "bad.modelfile")
        )
        payload = json.loads(output)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["file"], os.path.join(FIXTURES, "bad.modelfile"))
        codes = {f["code"] for f in payload[0]["findings"]}
        self.assertIn("MOD003", codes)

    def test_cli_stdin(self):
        code, output, _ = self.run_cli(stdin="from llama3\nPARAMETER temperature 0.7\n")
        self.assertEqual(code, 0)
        self.assertIn("MOD005", output)

    def test_cli_min_severity(self):
        code, output, _ = self.run_cli(
            "--min-severity", "error", os.path.join(FIXTURES, "bad.modelfile")
        )
        self.assertNotIn("MOD005", output)

    def test_cli_no_files_reads_stdin(self):
        code, output, _ = self.run_cli(stdin="FROM llama3\n")
        self.assertEqual(code, 0)

    def test_cli_fix_applies_in_place(self):
        path = os.path.join(FIXTURES, "fixme.modelfile")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("from llama3\nPARAMETER temperature 3.0\n")
        try:
            code, output, _ = self.run_cli("--fix", path)
            self.assertEqual(code, 0)
            with open(path, "r", encoding="utf-8") as handle:
                fixed = handle.read()
            self.assertEqual(fixed.split("\n")[0], "FROM llama3")
            self.assertIn("PARAMETER temperature 2", fixed.split("\n")[1])
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_cli_json_includes_codes(self):
        code, output, _ = self.run_cli(
            "--format", "json", os.path.join(FIXTURES, "bad.modelfile")
        )
        payload = json.loads(output)
        codes = {f["code"] for f in payload[0]["findings"]}
        self.assertIn("MOD003", codes)
        self.assertIn("MOD005", codes)
        self.assertEqual(payload[0]["file"], os.path.join(FIXTURES, "bad.modelfile"))

    def test_cli_unreadable_file_reports_error(self):
        code, output, error = self.run_cli("/nonexistent/no-such-file.modelfile")
        self.assertEqual(code, 1)
        self.assertIn("cannot read", error)


if __name__ == "__main__":
    unittest.main()
