"""Compatibility entry point; implementation lives in sandbox_checks."""
from scripts.sandbox_checks.accept_sandbox import (
    ROOT, check_receipts, workflows, run, main,
)


if __name__ == "__main__":
    main()
