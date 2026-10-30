"""Prove the suite catches real bugs: switch on each bug and expect failing tests.

A test suite that stays green while the app is broken is worthless. This script
re-runs the suite once per known bug and fails if any bug goes unnoticed.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import KNOWN_FAULTS  # noqa: E402


def run_with_fault(fault):
    env = {**os.environ, "TASKBOARD_FAULTS": fault}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider",
         "--override-ini=addopts=", "--output=/tmp/taskboard-fault-output"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    failed = re.findall(r"^(?:FAILED|ERROR) (\S+)", result.stdout, re.MULTILINE)
    return result.returncode, failed


def main():
    missed = []
    for fault in sorted(KNOWN_FAULTS):
        code, failed = run_with_fault(fault)
        caught = code == 1 and failed
        print(f"{'CAUGHT' if caught else 'MISSED'}  {fault:<22} {len(failed)} failing test(s)")
        for name in failed[:3]:
            print(f"        {name}")
        if not caught:
            missed.append(fault)
    if missed:
        print(f"\nNot caught: {', '.join(missed)}")
        return 1
    print(f"\nAll {len(KNOWN_FAULTS)} injected bugs were caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
