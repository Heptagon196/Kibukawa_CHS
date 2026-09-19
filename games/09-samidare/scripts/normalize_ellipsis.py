"""Normalize Chinese ellipses and remove redundant terminal full stops."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path

import pipeline as p


RUN = re.compile(r"…+")
REDUNDANT_STOP = re.compile(r"(?<=[…—])。")


def lengths(text: str) -> list[int]:
    return [len(match.group()) for match in RUN.finditer(text)]


def is_pure_pause(text: str) -> bool:
    return not text.strip("…。，！？!?、,.；;：:—－・ ·\t\r\n")


def normalized(source: str, target: str) -> str:
    source_runs = lengths(source)
    target_runs = lengths(target)
    result = target

    if target_runs:
        if len(source_runs) == len(target_runs) and source_runs:
            desired = source_runs
        elif source_runs and max(source_runs) == 1:
            desired = [1] * len(target_runs)
        elif not source_runs and not is_pure_pause(target):
            desired = [1] * len(target_runs)
        else:
            desired = None

        if desired is not None:
            iterator = iter(desired)
            result = RUN.sub(lambda _: "…" * next(iterator), result)

    # Japanese commonly writes 「…。」「ー。」.  A Chinese full stop after a
    # terminal ellipsis or em dash is redundant, including when the dash was
    # introduced to render a Japanese prolonged vowel.
    return REDUNDANT_STOP.sub("", result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    draft = p.WORK / "work/dialogue-tagged.json"
    data = json.loads(draft.read_text(encoding="utf-8"))
    changes = []
    for unit in data["units"]:
        if unit.get("kind", "line") != "line":
            continue
        before = unit.get("target", "")
        after = normalized(unit["source"], before)
        if after == before:
            continue
        changes.append({
            "script": unit["script"],
            "offset": unit["offset"],
            "source": unit["source"],
            "before": before,
            "after": after,
            "source_runs": lengths(unit["source"]),
            "before_runs": lengths(before),
            "after_runs": lengths(after),
        })
        if unit.get("runs"):
            desired = iter(lengths(after))
            updated_runs = [REDUNDANT_STOP.sub("", RUN.sub(lambda _: "…" * next(desired), part))
                            for part in unit["runs"]]
            if "".join(updated_runs) != after:
                raise ValueError(f"cannot preserve colour runs at {unit['script']}:{unit['offset']}")
            unit["runs"] = updated_runs
        unit["target"] = after

    report = {
        "changed_units": len(changes),
        "before_runs": dict(sorted(Counter(n for item in changes for n in item["before_runs"]).items())),
        "after_runs": dict(sorted(Counter(n for item in changes for n in item["after_runs"]).items())),
        "changes": changes,
    }
    report_path = p.WORK / "reports/ellipsis-normalization-preview.json"
    p.save(report_path, report)
    print(json.dumps({key: report[key] for key in ("changed_units", "before_runs", "after_runs")},
                     ensure_ascii=False))

    if not args.apply:
        print("PREVIEW", report_path)
        return

    folder = p.inside(p.WORK / "backups" / ("ellipsis_normalization_" + time.strftime("%Y%m%d_%H%M%S")))
    folder.mkdir(parents=True)
    shutil.copy2(draft, folder / draft.name)
    draft.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["backup"] = str(folder / draft.name)
    report["applied"] = True
    p.save(p.WORK / "reports/ellipsis-normalization.json", report)
    print("APPLIED", len(changes), "units")
    print("BACKUP", report["backup"])


if __name__ == "__main__":
    main()
