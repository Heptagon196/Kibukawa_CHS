"""Apply the independently reviewed colour-context corrections.

The proposal/review files are immutable QA artifacts.  Only this script writes the
approved (accept/revise) decisions back to the tagged dialogue, serially.
"""
import json
import os
from pathlib import Path


GAME = Path(__file__).resolve().parents[1]
DRAFT = GAME / "work/dialogue-tagged.json"
AUDIT_DIR = GAME / "work/colour_context_audit"
COLOUR_REPORT = GAME / "reports/text-colour-audit.json"
FINAL = AUDIT_DIR / "final.accepted.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    os.replace(temp, path)


def reviewed_entries():
    final = []
    for chapter in range(6):
        proposals = load(AUDIT_DIR / ("c%d.proposals.json" % chapter))
        reviews = load(AUDIT_DIR / ("c%d.review.json" % chapter))
        proposal_by_key = {(row["script"], row["offset"]): row for row in proposals}
        review_by_key = {(row["script"], row["offset"]): row for row in reviews}
        if len(proposal_by_key) != len(proposals):
            raise ValueError("duplicate proposal key in c%d" % chapter)
        if len(review_by_key) != len(reviews):
            raise ValueError("duplicate review key in c%d" % chapter)
        if set(proposal_by_key) != set(review_by_key):
            raise ValueError("proposal/review coverage differs in c%d" % chapter)
        for key, proposal in proposal_by_key.items():
            review = review_by_key[key]
            decision = review["decision"]
            if decision not in ("accept", "revise", "reject"):
                raise ValueError("unknown decision %r for %r" % (decision, key))
            if decision == "reject":
                continue
            row = {
                "script": key[0],
                "offset": key[1],
                "source": proposal["source"],
                "old": proposal["old"],
                "target": review["target"],
                "runs": review.get("runs"),
                "decision": decision,
                "reason": review.get("reason", ""),
            }
            final.append(row)
    return final


def apply_reviews():
    document = load(DRAFT)
    units = {(row["script"], row["offset"]): row for row in document["units"]}
    previous = {}
    if FINAL.exists():
        previous = {(row["script"], row["offset"]): row for row in load(FINAL)}
    colour_records = {
        (row["script"], row["offset"]): row
        for row in load(COLOUR_REPORT)["records"]
    }
    accepted = reviewed_entries()
    missing = {(row["script"], row["offset"]) for row in accepted} - set(units)
    if missing:
        raise KeyError("unknown dialogue units: %r" % sorted(missing))

    changed = 0
    for row in accepted:
        key = (row["script"], row["offset"])
        unit = units[key]
        if unit["source"] != row["source"]:
            raise ValueError("source drift at %r" % (key,))
        allowed_targets = {row["old"], row["target"]}
        if key in previous:
            allowed_targets.add(previous[key]["target"])
        if unit.get("target", "") not in allowed_targets:
            raise ValueError("target drift at %r: %r" % (key, unit.get("target")))
        runs = row["runs"]
        colour = colour_records.get(key)
        if colour and colour["mode"] == "mixed":
            if runs is None or len(runs) != len(colour["source_runs"]):
                raise ValueError("mixed-colour run count differs at %r" % (key,))
            if "".join(runs) != row["target"]:
                raise ValueError("runs do not join into target at %r" % (key,))
        elif runs is not None:
            raise ValueError("plain/whole-colour unit unexpectedly has runs at %r" % (key,))

        before = (unit.get("target", ""), unit.get("runs"))
        unit["target"] = row["target"]
        if runs is None:
            unit.pop("runs", None)
        else:
            unit["runs"] = runs
        if before != (unit["target"], unit.get("runs")):
            changed += 1

    save(DRAFT, document)
    save(FINAL, accepted)
    print("applied %d reviewed colour-context corrections (%d changed now)" %
          (len(accepted), changed))
    return len(accepted), changed


def main():
    apply_reviews()


if __name__ == "__main__":
    main()
