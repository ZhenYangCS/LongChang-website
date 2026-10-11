"""Prepare the anonymous site's assets from the paper's frozen source data.

Run with Python, Pillow and pypdf. No model/API calls are made.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
RESULTS = ROOT / "ACL/materials/results"


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def picture(source, name, width=1400, trim=False):
    im = Image.open(ROOT / source).convert("RGBA")
    if trim:
        im = im.crop(im.getbbox())
    im.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
    im.save(SITE / "assets/images" / (name + ".webp"), quality=88, method=6)


TABLE_LABELS = {
    "model_results_sol.tex": "tab:main-results",
    "controlled_comparisons_sol.tex": "tab:controlled-comparisons",
    "evolution_evaluation_table_sol.tex": "tab:evolution-evaluation",
}


def table_source(filename):
    path = RESULTS / filename
    if path.exists():
        return path, path.read_text()
    # The paper can also inline its tables into main.tex. Never fall back to
    # similarly named legacy tables: those may use an older discovery judge.
    path = ROOT / "ACL/main.tex"
    label = TABLE_LABELS[filename]
    blocks = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", path.read_text(), re.S)
    block = next(block for block in blocks if "\\label{" + label + "}" in block)
    return path, block


def table_rows(filename):
    rows = []
    for line in table_source(filename)[1].splitlines():
        if " & " in line and not line.lstrip().startswith(("&", "Model", "Condition", "\\")):
            row = [s.strip().replace("\\\\", "").strip() for s in line.split(" & ")]
            if re.fullmatch(r"\d+(\.\d+)?", row[1]):
                rows.append([row[0]] + [None if v == "--" else float(v) for v in row[1:]])
    return rows


def main():
    picture("ACL/figs/teaser/longchang_world.png", "glass-world", 1250, True)
    images = ["q_seq_before", "q_seq_motion", "q_seq_red_rest", "q_seq_red_restart",
              "q_seq_blue_rest", "q_seq_blue_restart", "v_seq_1_before", "v_seq_1_contact",
              "v_seq_3_before", "v_seq_3_contact", "weighing_flat_initial", "weighing_flat",
              "weighing_rimmed", "c_context_slide", "c_context_throw_red", "c_seq_finish"]
    for name in images:
        picture(f"ACL/figs/cases/studio_frames/{name}.png", name, 1200)
    picture("ACL/figs/apparatus/studio_apparatus.png", "pendulum", 1000)

    metrics = ["D", "C", "S", "R", "L", "ES", "CS", "CF", "AF"]
    models = [dict(name=row[0], **dict(zip(metrics, row[1:])))
              for row in table_rows("model_results_sol.tex")]
    assert len(models) == 12
    models.sort(key=lambda m: (-m["D"], -m["C"], -m["S"]))
    with (RESULTS / "sources/gpt_6_1_sol_episodes.csv").open() as f:
        episodes = list(csv.DictReader(f))
    assert len(episodes) == 540
    lookup = {m["name"].lower(): m for m in models}
    for m in models:
        subset = [e for e in episodes if e["model"].lower() == m["name"].lower()]
        assert len(subset) == 45
        altered = [e for e in subset if e["control"] == "False"]
        assert len(altered) == 42
        for metric, key in [("D", "success"), ("C", "correct"), ("S", "supported")]:
            assert round(100 * sum(e[key] == "True" for e in altered) / 42, 1) == m[metric]
        m["scenes"] = {}
        for scene_id in sorted({e["scene"] for e in altered}):
            es = [e for e in altered if e["scene"] == scene_id]
            m["scenes"][scene_id[:2]] = {k: sum(e[v] == "True" for e in es)
                                         for k, v in [("D", "success"), ("C", "correct"), ("S", "supported")]}

    # Public episode data deliberately contains results only, not local paths or request settings.
    public_keys = ["scene", "model", "repeat", "control", "correct", "supported", "success",
                   "turns_used", "early_done", "tools_built", "build_turns", "build_failure_turns",
                   "action_failure_turns"]
    with (SITE / "downloads/episodes.csv").open("w") as f:
        w = csv.DictWriter(f, public_keys)
        w.writeheader()
        w.writerows({k: e[k] for k in public_keys} for e in episodes)
    with (SITE / "downloads/model-results.csv").open("w") as f:
        w = csv.DictWriter(f, ["name"] + metrics, extrasaction="ignore")
        w.writeheader()
        w.writerows(models)

    names = ["Normal control", "Red attraction", "Mass-dependent fall", "Oscillating gravity",
             "High-speed braking", "Clockwise deflection", "Tile rebounds", "Speed limit",
             "Boundary crossing", "Acceleration zone", "Collision boost", "Color exchange",
             "Third-contact jump", "Delayed velocity copy", "Interrupted drift"]
    descriptions = [
        "A gray tile looks different. Does it change how objects move?",
        "Red and blue spheres share a room. Which pairs move toward each other?",
        "Two balls have different masses. How does that affect their fall?",
        "Identical experiments can behave differently at different times.",
        "Slow motion looks ordinary. Faster motion tells a different story.",
        "A straight launch need not produce a straight path.",
        "Two colored tiles give the same ball very different rebounds.",
        "Larger impulses bring smaller and smaller gains in speed.",
        "Crossing the edge of a gray tile changes a ball's motion.",
        "Motion inside the yellow region has an additional source of energy.",
        "Ball–ball contact can change more than the direction of motion.",
        "The objects keep their identities. Their colors may not stay with them.",
        "Similar collisions can have different outcomes. Does their history matter?",
        "One ball moves long after another was launched. Are the events connected?",
        "A red ball starts moving by itself. Intervening can make the effect disappear.",
    ]
    families = ["Control", "Object properties", "Object properties", "Time", "Motion", "Motion",
                "Contact", "Motion", "Space", "Space", "Contact", "Contact", "History", "Time", "History"]
    raw_scenes = read_json(ROOT / "scenes/base_15.json")["scenes"]
    scenes = []
    for i, s in enumerate(raw_scenes):
        scenes.append(dict(id=s["id"][:2], key=s["id"], name=names[i], description=descriptions[i],
                           family=families[i], law=s["oracle"]["ground_truth"],
                           image=f"assets/images/scene-{i+1:02}.webp"))
    # Use the paper's precise current wording for the public overview of Scene 15.
    scenes[14]["law"] = ("An extra northward acceleration of 1.5 bricks/count² acts on the red ball. "
        "A nonzero push or throw on any movable object pauses this force for 10 counts. "
        "Another such action restarts the pause. Gravity, friction and collisions still act.")
    write_json(SITE / "downloads/scenes.json", {"units": "bricks and counts; one count corresponds to one simulated second", "scenes": scenes})

    evidence = read_json(ROOT / "ACL/materials/cases/sources/evidence.json")
    tool = read_json(ROOT / "ACL/materials/cases/sources/tool_case.json")
    public_evidence = {
        "description": "Selected original notes and observations used in the project page. Editorial explanations are separate from quoted notes.",
        "question": {"scene": "15", "model": "GPT-6-Astra", "repeat": 2, "budget": 100,
                     "notes": evidence["question"]["notes"]},
        "checklist": {"scene": "15", "model": "Gemini-3.7-Flash", "repeat": 1, "budget": 100,
                      "steps": evidence["checklist"]["public_steps"],
                      "motion_events": evidence["checklist"]["turn2_transitions"]},
        "color": {"scene": "12", "model": "GPT-6-Astra", "repeat": 1, "budget": 500,
                  "notes": evidence["partial"]["notes"]},
        "apparatus": {"scene": "15", "model": "GPT-6-Astra", "repeat": 2, "budget": 500,
                      "notes": tool["notes"], "pan_readings": tool["pan_readings"],
                      "flat_pan_readings": tool["flat_pan_readings"]},
    }
    write_json(SITE / "downloads/case-records.json", public_evidence)

    controlled_rows = table_rows("controlled_comparisons_sol.tex")
    controlled = [dict(name=r[0], **dict(zip(["D", "C", "S", "L", "AF"], r[1:]))) for r in controlled_rows]
    assert len(controlled) == 6
    evolution = [dict(name=r[0], C=r[1], S=r[2], D=r[3]) for r in table_rows("evolution_evaluation_table_sol.tex")]
    assert len(evolution) == 5
    write_json(SITE / "downloads/controlled-results.json", {"controlled": controlled, "evolution": evolution})

    # Keep the download portable and anonymous, including PDF metadata.
    writer = PdfWriter()
    for page in PdfReader(ROOT / "acl-build/0.pdf").pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": "Can LLMs Uncover the Laws of Their World?", "/Author": "Anonymous Authors"})
    with (SITE / "downloads/paper.pdf").open("wb") as f:
        writer.write(f)
    with zipfile.ZipFile(SITE / "downloads/prompts.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name in ["exploration_prompt.txt", "report_prompt.txt", "discovery_judge.txt"]:
            candidates = list((ROOT / "ACL/materials/prompts/sources").glob(name))
            if candidates:
                z.write(candidates[0], name)
        # Actual source naming is preserved inside the archive.
        if len(z.namelist()) < 3:
            for p in (ROOT / "ACL/materials/prompts/sources").glob("*.txt"):
                if any(k in p.name for k in ("explor", "report", "judg")) and p.name not in z.namelist():
                    z.write(p, p.name)

    # A self-contained source download keeps the code accessible even when
    # the paper's anonymous repository requires authorization.
    bundle_readme = """# LongChang — Anonymous source bundle

Implementation accompanying 'Can LLMs Uncover the Laws of Their World?'.

This archive contains the framework's Python sources, the base scenes and
dependency list. API credentials, machine-specific launchers and run logs
are not included. Sources are a snapshot of the current implementation;
paper results use the frozen evaluations documented on the project page.

## Getting started

Use Python 3.12 or later in a virtual environment:

```bash
python -m pip install -r requirements.txt
python longchang/run.py --help
python longchang/run.py list --benchmark scenes/base_15.json --ids-only
```

The list command does not call a model. For model-backed experiments,
provide your own BASE_URL, API_KEY, MODEL, JUDGE_MODEL and BUILD_REVIEW_MODEL
environment variables. See each command's --help for its options.

The MuJoCo environment, action interface, apparatus support, explorer,
evaluation and scene evolution code are in longchang/. Prompts are in
longchang/prompts/. The paper's 15 base worlds are in scenes/base_15.json.
"""
    bundle_files = sorted((ROOT / "longchang").rglob("*.py"))
    bundle_files += [ROOT / "requirements.txt", ROOT / "scenes/base.json", ROOT / "scenes/base_15.json"]
    with zipfile.ZipFile(SITE / "downloads/longchang-source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("LongChang/README.md", bundle_readme)
        for path in bundle_files:
            text = path.read_text()
            assert not re.search(r"/root/|/Users/|/home/", text), path
            z.writestr("LongChang/" + str(path.relative_to(ROOT)), text)

    data = dict(models=models, scenes=scenes, controlled=controlled, evolution=evolution,
                evidence=public_evidence,
                setup={"models": 12, "scenes": 15, "repeats": 3, "episodes": 540,
                       "budget": 100, "judge": "GPT-6.1-Sol", "altered_episodes_per_model": 42})
    (SITE / "data/paper.js").write_text("window.LONGCHANG = " + json.dumps(data, ensure_ascii=False) + ";\n")
    hashes = {}
    for path in [RESULTS / "sources/gpt_6_1_sol_episodes.csv"]:
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    table_hashes = {}
    for filename, label in TABLE_LABELS.items():
        path, source = table_source(filename)
        table_hashes[label] = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(source.encode()).hexdigest(),
                               "inline": path.name == "main.tex"}
    write_json(SITE / "data/provenance.json", {"sources": hashes, "tables": table_hashes, "judge": "GPT-6.1-Sol",
        "episodes": 540, "policy": "Metrics follow the current paper's frozen rejudging; control runs are excluded from D/C/S. Case studies are selected illustrations, not additional aggregate results."})
    print(f"Prepared {len(models)} models, {len(scenes)} scenes and {len(episodes)} verified episodes.")


if __name__ == "__main__":
    main()
