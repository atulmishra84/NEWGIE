"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from context_intelligence.application.scan_service import scan_folder


def main() -> None:
    parser = argparse.ArgumentParser(prog="gie-context", description="GIE Context Intelligence CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a local folder")
    scan.add_argument("path", type=Path)
    scan.add_argument("--output", "-o", type=Path, help="Write context model JSON")
    scan.add_argument("--tenant", default="default")

    args = parser.parse_args()
    if args.command == "scan":
        model = scan_folder(args.path, tenant_id=args.tenant)
        payload = model.model_dump(mode="json")
        text = json.dumps(payload, indent=2)
        if args.output:
            args.output.write_text(text)
        else:
            sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
