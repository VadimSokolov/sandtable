#!/usr/bin/env python3
"""Copy saved viewer inputs/results byte-for-byte; never execute external code."""

import argparse, hashlib, json, shutil
from pathlib import Path


def import_archives(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    copied = []
    if source == destination:
        raise ValueError("Source and destination must differ.")
    for name in ["data", "scenario_library", "examples", "sponsor_scenarios"]:
        folder = source / name
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            relative = path.relative_to(source)
            target = destination / relative
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError("Conflicting existing archive: " + str(relative))
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(path, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError("Copy verification failed: " + str(relative))
            copied.append(dict(file=str(relative), sha256=expected))
    return dict(source=str(source), destination=str(destination), files=copied)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument(
        "--destination",
        default=str(Path(__file__).resolve().parents[1] / "studies/convoy-study/mission-viewer-v3"),
    )
    args = parser.parse_args()
    report = import_archives(args.source, args.destination)
    Path(args.destination).mkdir(parents=True, exist_ok=True)
    (Path(args.destination) / "archive-import.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified {len(report['files'])} archive files.")


if __name__ == "__main__":
    main()
