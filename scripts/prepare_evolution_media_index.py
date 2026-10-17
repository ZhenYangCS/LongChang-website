"""Publish small, content-versioned URLs for the evolution videos and posters."""
import hashlib
import json
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]


def write_index(demos=None):
    if demos is None:
        demos = json.loads((SITE / 'data/evolution-demos.json').read_text())['demos']
    index = {}
    for demo in demos:
        index[demo['id']] = {}
        for kind in ['video', 'poster']:
            path = demo[kind]
            version = hashlib.sha256((SITE / path).read_bytes()).hexdigest()[:12]
            index[demo['id']][kind] = f'{path}?v={version}'
    target = SITE / 'data/evolution-media.js'
    temporary = target.with_suffix('.js.tmp')
    temporary.write_text('window.EVOLUTION_MEDIA = ' + json.dumps(index, separators=(',', ':')) + ';\n')
    temporary.replace(target)
    return index


if __name__ == '__main__':
    write_index()
