"""Validate source-bound English summaries and export their complete download."""
import hashlib
import json
from pathlib import Path
import re

SITE = Path(__file__).resolve().parents[1]


def main():
    evidence = SITE/'data/result-evidence'
    manifest = json.loads((evidence/'manifest.json').read_text())
    summaries = {}
    for path in sorted((SITE/'data/judge-summaries').glob('*.json')):
        group = json.loads(path.read_text())
        assert group['kind'] == 'English summary' and group['language'] == 'en'
        assert len(group['runs']) == 45
        for entry in group['runs']:
            assert entry['episode_id'] not in summaries
            assert entry['summary'].strip() and len(entry['summary']) <= 400
            assert not re.search(r'[\u3400-\u9fff]', entry['summary'])
            summaries[entry['episode_id']] = (group['model'], entry)
    entries = []
    for path in manifest['paths']:
        group = json.loads((evidence/path).read_text())
        for run in group['runs']:
            model, summary = summaries.pop(run['id'])
            assert model == group['model']
            assert summary['scene'] == group['scene'] and summary['repeat'] == run['repeat']
            assert summary['evaluation_sha256'] == run['evaluation_sha256']
            assert summary['reason_sha256'] == hashlib.sha256(run['reason'].encode()).hexdigest()
            entries.append(dict(**summary, model=model, D=run['D'], C=run['C'], S=run['S'],
                                control=run['control'], accepted=run['accepted'], original_json=run['archive']))
    assert not summaries and len(entries) == manifest['episodes'] == 540
    output = dict(schema_version=1, language='en', kind='English summaries', judge=manifest['judge'],
                  description='Editorial English summaries of the recorded judge reasons, not new evaluations or verbatim translations. Complete original reports and judge reasons remain in the original JSON archives.',
                  source_index_sha256=manifest['source_sha256'], original_archive=manifest['archive'], runs=entries)
    encoded = json.dumps(output, ensure_ascii=False, indent=2)+'\n'
    assert not re.search(r'[\u3400-\u9fff]', encoded)
    path = SITE/'downloads/longchang-judge-summaries-en.json'
    path.write_text(encoded)
    print(f'PASS: {len(entries)} English summaries match the original episode IDs, evaluations and reason hashes; exported {path.name}.')


if __name__ == '__main__':
    main()
