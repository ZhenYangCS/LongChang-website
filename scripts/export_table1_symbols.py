"""Use the paper's actual Table 1 mechanism drawings in the scene selector."""
import hashlib,json,re,subprocess,tempfile
from pathlib import Path
from pypdf import PdfReader

SITE=Path(__file__).resolve().parents[1]
SOURCE=SITE.parent/'ACL/secs/02_introduction.tex'

def main():
    source=SOURCE.read_text()
    definitions=source[source.index(r'\definecolor{sceneink}'):source.index(r'\newcommand{\scenecard}')]
    definitions=definitions.replace(r'\relax\space','')
    tex='\\documentclass{article}\n\\usepackage{tikz}\n\\usepackage[paperwidth=88pt,paperheight=30pt,margin=0pt]{geometry}\n\\usetikzlibrary{arrows.meta,calc}\n\\pagestyle{empty}\n\\setlength{\\topskip}{0pt}\n\\setlength{\\parindent}{0pt}\n'+definitions+'\n\\begin{document}\n'
    tex+='\n\\newpage\n'.join(r'\vspace*{4pt}\noindent\hspace*{6pt}\scenesymbol{'+str(i)+'}' for i in range(1,16))+'\n\\end{document}\n'
    out=SITE/'assets/table1';out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='longchang-table1-') as tmp:
        path=Path(tmp);(path/'symbols.tex').write_text(tex)
        result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','symbols.tex'],cwd=path,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stdout[-4000:])
        assert len(PdfReader(path/'symbols.pdf').pages)==15
        for i in range(1,16):
            target=out/f'scene-{i:02}.svg'
            subprocess.run(['pdftocairo','-svg','-f',str(i),'-l',str(i),str(path/'symbols.pdf'),str(target)],check=True)
    (out/'source.json').write_text(json.dumps(dict(source='ACL/secs/02_introduction.tex',table='tab:scene-overview',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),description='Exact mechanism drawings from Table 1; titles are populated from the same paper scene catalogue.'),indent=2)+'\n')
    print('Exported all 15 original Table 1 mechanism symbols as SVG.')

if __name__=='__main__':main()
