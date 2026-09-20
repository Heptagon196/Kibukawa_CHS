"""Rebuild the authoritative draft and apply reviewed QA fixes atomically.

The extraction copy supplies immutable unit metadata and the last collected cache
supplies every translated tagged target.  This makes recovery deterministic even
if an interrupted bulk edit leaves work/dialogue-tagged.json unreadable.
"""
import argparse
import json
import re
from pathlib import Path

import pipeline as p


MANIFESTS = (
    "semantic01.json", "semantic02.json", "semantic03.json",
    "semantic04.json", "semantic05.json", "semantic06.json",
    "empty_rows.json", "punctuation.json", "color_terms.json",
)

INFO_LAYOUT_UNITS = {
    "scratch4.dat/s27:114", "scratch4.dat/s27:353", "scratch4.dat/s27:23889",
    "scratch4.dat/s31:178", "scratch4.dat/s31:7459", "scratch4.dat/s31:11051",
    "scratch4.dat/s33:15570", "scratch4.dat/s34:219", "scratch4.dat/s34:17793",
    "file/append:6526",
}
TAG = re.compile(r"<[^>]+>")
INFO_PADDING = re.compile(r"^(<color=\d+>.*?</color><color=0>)(　*)( ?)(</color>.*)$")


def native_info_width(text):
    return sum(6 if ord(value) <= 0x7f or 0xff61 <= ord(value) <= 0xff9f else 12
               for value in TAG.sub("", text))


def fit_info_padding(unit):
    """Shrink only the inherited name/date padding, preserving all INFO text."""
    if unit["id"] not in INFO_LAYOUT_UNITS:
        return False
    match = INFO_PADDING.match(unit["target"])
    p.require(match is not None, "Missing INFO alignment padding: " + unit["id"])
    cells = match.group(2)
    changed = bool(match.group(3))
    if changed:
        unit["target"] = match.group(1) + cells + match.group(4)
    width = native_info_width(unit["target"])
    if width <= 240:
        return changed
    excess = width - 240
    remove_cells, remainder = divmod(excess, 12)
    p.require(remainder in (0, 6), "Unsupported INFO alignment delta: " + unit["id"])
    consumed = remove_cells + (1 if remainder else 0)
    p.require(len(cells) >= consumed, "Insufficient INFO alignment padding: " + unit["id"])
    replacement = cells[:-consumed]
    unit["target"] = match.group(1) + replacement + match.group(4)
    p.require(native_info_width(unit["target"]) <= 240, "INFO alignment still exceeds 240px: " + unit["id"])
    return True


def proposed_rows(folder):
    proposals = {}
    for name in MANIFESTS:
        document = p.load(folder / name)
        rows = document.get("changes") or document.get("fixes") or document.get("text_fixes") or []
        for row in rows:
            current = row.get("current_target", row.get("before"))
            target = row.get("replacement_target", row.get("suggested_target", row.get("target")))
            p.require(current is not None and target is not None, "Incomplete QA proposal: " + row["id"])
            proposals.setdefault(row["id"], []).append((name, current, target))
    return proposals


def reviewed_targets(folder, proposals):
    review = p.load(folder / "integration-review.json")
    revised = {row["id"]: row["replacement_target"] for row in review["rejected_or_revise"]}
    duplicates = {row["id"]: row for row in review["duplicate_resolution"]}
    final = {}
    for unit_id, rows in proposals.items():
        if unit_id in revised:
            final[unit_id] = revised[unit_id]
            continue
        duplicate = duplicates.get(unit_id)
        if duplicate:
            if "replacement_target" in duplicate:
                final[unit_id] = duplicate["replacement_target"]
            elif duplicate["decision"] == "use_semantic02":
                final[unit_id] = next(target for name, _, target in rows if name == "semantic02.json")
            elif duplicate["decision"] == "use_semantic06":
                final[unit_id] = next(target for name, _, target in rows if name == "semantic06.json")
            elif duplicate["decision"] == "use_revised_target":
                final[unit_id] = revised[unit_id]
            else:
                raise ValueError("Unknown duplicate decision: " + repr(duplicate))
            continue
        values = {target for _, _, target in rows}
        p.require(len(values) == 1, "Unresolved QA proposals: " + unit_id)
        final[unit_id] = values.pop()
    p.require(len(final) == review["review_scope"]["unique_text_units"], "QA review unit count mismatch")
    return final


def rebuild():
    fixes = p.WORK / "work/fixes"
    proposals = proposed_rows(fixes)
    final = reviewed_targets(fixes, proposals)

    template = p.load(p.WORK / "texts/dialogue-tagged.json")
    cache = p.load(p.WORK / "work/cache.json")
    cached = {}
    for file in cache["files"].values():
        for item in file["items"]:
            extra = item.get("extra", {})
            location = extra.get("location", {})
            if location.get("kind") == "script":
                cached[location["unit_id"]] = extra

    p.require(len(template["units"]) == 9850 and len(cached) == 9850, "Incomplete recovery inputs")
    changed = []
    info_layout_changed = []
    for unit in template["units"]:
        extra = cached[unit["id"]]
        p.require(extra["tagged_source"] == unit["source"], "Stale cached source: " + unit["id"])
        unit["target"] = extra["tagged_target"]
        unit["translation_status"] = "inactive_copy" if not unit["active"] else "draft"
        if unit["id"] in final:
            expected = {current for _, current, _ in proposals[unit["id"]]}
            if unit["target"] not in expected and unit["target"] != final[unit["id"]]:
                raise ValueError("Stale QA target: " + unit["id"])
            before = unit["target"]
            unit["target"] = final[unit["id"]]
            if before != unit["target"]:
                changed.append(unit["id"])
        if fit_info_padding(unit):
            info_layout_changed.append(unit["id"])

    p.save(p.WORK / "work/dialogue-tagged.json", template)
    p.require(set(info_layout_changed).issubset(INFO_LAYOUT_UNITS), "Unexpected INFO layout change")
    report = dict(schema=1, reviewed_units=len(final), changed_from_cache=len(changed),
                  info_layout_units=len(INFO_LAYOUT_UNITS), info_layout_changed_from_cache=len(info_layout_changed),
                  recovered_units=len(template["units"]), integration_review="work/fixes/integration-review.json",
                  dialogue_sha256=p.sha((p.WORK / "work/dialogue-tagged.json").read_bytes()))
    p.save(p.WORK / "reports/qa-fixes-applied.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(rebuild(), ensure_ascii=False))
