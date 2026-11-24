# Renders a sanitized committed test report from a real pytest JUnit run.
import argparse
import platform
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def base_commit() -> str:
    result = subprocess.run(
        ["/usr/bin/git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--command", required=True)
    parser.add_argument("--coverage", default="not measured")
    arguments = parser.parse_args()
    tree = ET.parse(arguments.junit)
    suite = tree.getroot().find("testsuite")
    if suite is None:
        raise SystemExit("missing testsuite")
    suite.attrib.pop("hostname", None)
    arguments.output_directory.mkdir(parents=True, exist_ok=True)
    tree.write(arguments.output_directory / "junit.xml", encoding="utf-8", xml_declaration=True)
    tests = int(suite.attrib["tests"])
    failures = int(suite.attrib["failures"])
    errors = int(suite.attrib["errors"])
    skipped = int(suite.attrib["skipped"])
    lines = [
        "# Test Report",
        "",
        f"- Generated (UTC): {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Base commit: `{base_commit()}` (the report is committed on top of it)",
        f"- Python: {platform.python_version()} on {platform.system()}",
        f"- Command: `{arguments.command}`",
        f"- Tests: {tests}",
        f"- Passed: {tests - failures - errors - skipped}",
        f"- Failed: {failures}",
        f"- Errors: {errors}",
        f"- Skipped: {skipped}",
        f"- Line and branch coverage of `src/m15`: {arguments.coverage}",
        "",
    ]
    (arguments.output_directory / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
