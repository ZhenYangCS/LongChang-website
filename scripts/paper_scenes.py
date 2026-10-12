"""Canonical scene names from the current ACL scene-overview table."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def paper_scene_names():
    pending = [ROOT / 'ACL/main.tex']
    seen = set()
    while pending:
        path = pending.pop(0).resolve()
        if path in seen:
            continue
        seen.add(path)
        text = re.sub(r'(?<!\\)%[^\n]*', '', path.read_text())
        if r'\label{tab:scene-overview}' in text:
            pairs = re.findall(r'\\scenecard\{(\d{2})\}\{([^}]+)\}', text)
            if pairs:
                names = dict(pairs)
                assert len(pairs) == 15 and set(names) == {f'{i:02}' for i in range(1, 16)}
                return names, path
        for source in re.findall(r'\\(?:input|include)\{([^}]+)\}', text):
            candidate = (ROOT / 'ACL' / source).with_suffix('.tex')
            if candidate.is_file():
                pending.append(candidate)
    raise ValueError('Cannot find all 15 canonical scene names in the active ACL paper')


def paper_scene_laws():
    """Readable text of the actual appendix rows, including object scope."""
    names,_=paper_scene_names()
    path=ROOT/'ACL/secs/08_appendix.tex'
    text=path.read_text()
    rows=re.findall(r'^\s*(\d{2}) ([^&\n]+) & (.*?)\\\\\s*$',text,re.M)
    laws={}
    for number,name,law in rows:
        if number not in names:continue
        assert name.strip()==names[number],f'Appendix/overview name mismatch for {number}'
        law=law.replace('$','').replace('~',' ')
        law=re.sub(r'\\sqrt\{([^}]+)\}',r'√(\1)',law)
        law=re.sub(r'\\(?:mathbf|mathrm|texttt)\{([^}]+)\}',r'\1',law)
        for command,replacement in [(r'\geq','≥'),(r'\leq','≤'),(r'\pi','π'),(r'\sin','sin'),(r'\max','max')]:
            law=law.replace(command,replacement)
        law=re.sub(r'_\{([^}]+)\}',r'_\1',law)
        law=re.sub(r'\^\{([^}]+)\}',r'^\1',law)
        laws[number]=' '.join(law.split())
    assert set(laws)==set(names),'All 15 appendix laws are required'
    return laws,path
