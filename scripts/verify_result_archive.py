"""Verify an extracted LongChang JSON archive using only the standard library."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def verify(read):
    manifest = json.loads(read('manifest.json'))
    seen, groups = set(), Counter()
    scores = defaultdict(lambda: dict(runs=0, D=0, C=0, S=0, controls=0, rejected=0))
    turns = 0
    for run in manifest['runs']:
        episode = run['episode_id']
        assert episode not in seen, f'Duplicate episode: {episode}'
        seen.add(episode)
        payloads = [read(run['session_file']), read(run['evaluation_file'])]
        for payload, key in zip(payloads, ['session_sha256', 'eval_sha256']):
            assert hashlib.sha256(payload).hexdigest() == run[key], f'Hash mismatch: {episode} / {key}'
        session, evaluation = map(json.loads, payloads)
        assert session['episode_id'] == evaluation['episode_id'] == episode
        assert session['model'].lower() == run['model'].lower()
        assert session['tell'] == run['tell'] and session['budget'] == int(run['budget'])
        assert evaluation['status'] == 'complete'
        assert evaluation['judge_model'].lower() == 'gpt-6.1-sol'
        judgement = evaluation['judgement']
        control = run['control'] == 'True'
        assert judgement['correct'] == (run['correct'] == 'True')
        assert judgement['supported'] == (None if control else run['supported'] == 'True')
        success = judgement['correct'] and (control or judgement['supported'])
        assert success == (run['success'] == 'True')
        assert len(session['turns']) == int(run['turns_used'])
        turns += len(session['turns'])
        groups[(run['model'], run['scene'], int(run['repeat']))] += 1
        score = scores[run['model']]
        if control:
            score['controls'] += 1
            score['rejected'] += not judgement['correct']
        else:
            score['runs'] += 1
            for key, value in [('D', success), ('C', judgement['correct']), ('S', judgement['supported'])]:
                score[key] += value
    if manifest['scope'] == 'Complete main study':
        assert len(seen) == manifest['episodes'] == 540
        assert len(manifest['models']) == 12 and len(manifest['scenes']) == 15
        assert manifest['repeats'] == [1, 2, 3]
        expected = {(model, scene, repeat) for model in manifest['models']
                    for scene in manifest['scenes'] for repeat in manifest['repeats']}
        assert set(groups) == expected and all(count == 1 for count in groups.values())
        assert turns == 30223
        for model, score in sorted(scores.items()):
            assert score['runs'] == 42 and score['controls'] == 3
            rates = ' / '.join(f'{100*score[key]/42:.1f}%' for key in ['D', 'C', 'S'])
            print(f'{model}: D/C/S {rates}; normal reports rejected {score["rejected"]}/3')
    print(f'PASS: {len(seen)} complete session/evaluation pairs, original hashes, conditions and verdicts; {turns:,} turns.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    verify(lambda name: (args.directory/name).read_bytes())


if __name__ == '__main__':
    main()
