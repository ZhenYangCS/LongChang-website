"""Export every frozen main-study report, verdict and original turn record."""
import csv
import gzip
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
BASE = ROOT/'runs/main-15-20260930-022640-2180080'
SOURCE = ROOT/'ACL/non_submission/materials/results/sources/gpt_6_1_sol_episodes.csv'
TURN_FIELDS = ('turn', 'note', 'act', 'outcome', 'observation', 'result_observation', 'raw')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source_paths(row):
    folders = {folder.name.lower(): folder for folder in (BASE/row['scene']).iterdir() if folder.is_dir()}
    session = folders[row['model'].lower()]/f'r{row["repeat"]}'/'T0/session.json'
    evaluation = Path(row['eval_path'])
    return session, evaluation if evaluation.is_absolute() else ROOT/evaluation


def zip_member(archive, name, payload):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload, compresslevel=9)


def export_archives(rows, models):
    archive_name = 'downloads/longchang-main-study-json.zip'
    entries = []
    instructions = b'''LongChang main-study JSON records

All 540 paper runs: 12 models x 15 scenes x 3 repeats, including failed
discoveries and the normal control. This package covers the main study;
controlled comparisons and evolved-scene experiments are separate studies.

session.json and evaluation.json are unmodified, byte-for-byte copies of the
frozen files used for the paper. Session files include the actual prompts,
scene programs, rules, rubrics, request settings, all recorded turns, final
reports, report attempts and apparatus reviews. Evaluation files include the
judge prompt, attempts, raw responses, normalization and final judgement.
These are the complete JSON records; binary physics replay files are separate.

manifest.json maps every run to its conditions, scores and original SHA-256
hashes. Machine-specific evaluation paths from the source index are replaced
by portable archive paths; the two original JSON files are not rewritten.
The source-index hash identifies the frozen CSV used to select the paper runs.

To verify file integrity, coverage and scores after extracting this archive:
    python3 verify.py
This uses only the Python standard library. It does not call any model API.
'''
    verifier = (SITE/'scripts/verify_result_archive.py').read_bytes()
    with zipfile.ZipFile(SITE/archive_name, 'w') as complete:
        for number, row in enumerate(rows, 1):
            session_path, eval_path = source_paths(row)
            session_bytes, eval_bytes = session_path.read_bytes(), eval_path.read_bytes()
            assert digest(session_bytes) == row['session_sha256'], session_path
            assert digest(eval_bytes) == row['eval_sha256'], eval_path
            model = models[row['model'].lower()]['name']
            scene = row['scene'][:2]
            entry = {key: value for key, value in row.items() if key != 'eval_path'}
            entry['model'] = model
            entry['session_file'] = 'session.json'
            entry['evaluation_file'] = 'evaluation.json'
            name = f'downloads/result-json/{model.lower()}/{scene}-r{row["repeat"]}.zip'
            (SITE/name).parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(SITE/name, 'w') as single:
                zip_member(single, 'session.json', session_bytes)
                zip_member(single, 'evaluation.json', eval_bytes)
                zip_member(single, 'manifest.json', encode(dict(schema_version=1, scope='Single main-study run', runs=[entry])))
                zip_member(single, 'verify.py', verifier)
            prefix = f'{model.lower()}/{scene}/r{row["repeat"]}'
            entry = dict(entry, session_file=f'{prefix}/session.json', evaluation_file=f'{prefix}/evaluation.json')
            zip_member(complete, entry['session_file'], session_bytes)
            zip_member(complete, entry['evaluation_file'], eval_bytes)
            entries.append(entry)
            if number % 90 == 0:
                print(f'Archived {number}/{len(rows)} original JSON pairs.', flush=True)
        archive_manifest = dict(schema_version=1, scope='Complete main study', episodes=len(entries),
                                source_index_sha256=digest(SOURCE.read_bytes()),
                                models=sorted({entry['model'] for entry in entries}),
                                scenes=sorted({entry['scene'] for entry in entries}), repeats=[1, 2, 3], runs=entries)
        zip_member(complete, 'manifest.json', encode(archive_manifest))
        zip_member(complete, 'README.txt', instructions)
        zip_member(complete, 'verify.py', verifier)
    path = SITE/archive_name
    assert path.stat().st_size < 100_000_000, 'Archive exceeds the static repository file limit'
    return dict(path=archive_name, bytes=path.stat().st_size, sha256=digest(path.read_bytes()))


def parse_report(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    match = re.fullmatch(r'```(?:json|text)?[ \t]*\r?\n([\s\S]*?)\r?\n```', text, re.I)
    return json.loads(match[1].strip() if match else text)


def main():
    with SOURCE.open() as stream:
        rows = list(csv.DictReader(stream))
    paper = json.loads((SITE/'data/paper.js').read_text().removeprefix('window.LONGCHANG = ').rstrip(';\n'))
    models = {model['name'].lower(): model for model in paper['models']}
    output = SITE/'data/result-evidence'
    (output/'records').mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    record_bytes = 0
    total_turns = 0
    for row in rows:
        session_path, eval_path = source_paths(row)
        session_bytes, eval_bytes = session_path.read_bytes(), eval_path.read_bytes()
        assert digest(session_bytes) == row['session_sha256'], session_path
        assert digest(eval_bytes) == row['eval_sha256'], eval_path
        session, evaluation = json.loads(session_bytes), json.loads(eval_bytes)
        assert session['episode_id'] == evaluation['episode_id'] == row['episode_id']
        verdict = evaluation['judgement']
        control = row['control'] == 'True'
        assert verdict['correct'] == (row['correct'] == 'True')
        assert verdict['supported'] == (None if control else row['supported'] == 'True')
        assert (verdict['correct'] and (control or verdict['supported'])) == (row['success'] == 'True')
        report = parse_report(session['report'])
        assert isinstance(report, dict) and isinstance(report.get('conclusions'), list)
        turns = [{key: turn.get(key) for key in TURN_FIELDS} for turn in session['turns']]
        turn_ids = {turn['turn'] for turn in turns}
        for conclusion in report['conclusions']:
            assert set(conclusion.get('evidence_turns', [])) <= turn_ids
        record = dict(episode_id=row['episode_id'], report=session['report'], turns=turns)
        record_payload = encode(record)
        compressed = gzip.compress(record_payload, compresslevel=9, mtime=0)
        record_name = f'data/result-evidence/records/{row["episode_id"]}.json.gz'
        (SITE/record_name).write_bytes(compressed)
        total_turns += len(turns)
        record_bytes += len(compressed)
        model = models[row['model'].lower()]
        scene = row['scene'][:2]
        groups[(model['name'], scene)].append(dict(
            id=row['episode_id'], repeat=int(row['repeat']), control=control,
            D=None if control else row['success'] == 'True', C=verdict['correct'], S=verdict['supported'],
            accepted=verdict['correct'] if control else None,
            report=report, reason=verdict['reason'], action_errors=verdict['action_errors'],
            normalization=evaluation.get('report_normalization', []),
            truth=session['truth'], rubric=session.get('rubric'),
            turn_count=len(turns), record=record_name,
            archive=f'downloads/result-json/{model["name"].lower()}/{scene}-r{row["repeat"]}.zip',
            session_sha256=row['session_sha256'], evaluation_sha256=row['eval_sha256'],
            record_sha256=digest(record_payload)))
    for (name, scene), runs in groups.items():
        assert sorted(run['repeat'] for run in runs) == [1, 2, 3]
        model = models[name.lower()]
        if scene != '01':
            for key in ('D', 'C', 'S'):
                assert sum(run[key] for run in runs) == model['scenes'][scene][key]
        else:
            assert sum(not run['accepted'] for run in runs) == model['R']
        folder = output/name.lower()
        folder.mkdir(exist_ok=True)
        (folder/f'{scene}.json').write_bytes(encode(dict(model=name, scene=scene, judge='GPT-6.1-Sol', runs=sorted(runs, key=lambda run: run['repeat']))))
    assert len(rows) == 540 and len(groups) == 180
    archive = export_archives(rows, models)
    manifest = dict(episodes=len(rows), model_scenes=len(groups), turns=total_turns,
                    judge='GPT-6.1-Sol', source_sha256=digest(SOURCE.read_bytes()),
                    compressed_record_bytes=record_bytes, archive=archive,
                    paths=[f'{model.lower()}/{scene}.json' for model, scene in sorted(groups)])
    (output/'manifest.json').write_bytes(encode(manifest))
    print(f'Exported {len(rows)} reports, {len(groups)} model/scene groups and {total_turns:,} turns; records {record_bytes/1024/1024:.1f} MiB.')


if __name__ == '__main__':
    main()
