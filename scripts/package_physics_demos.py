"""Package the completed native demonstrations without rerunning physics."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

SITE=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args()
    demos=json.loads((SITE/'data/physics.js').read_text().removeprefix('window.PHYSICS_DEMOS = ').rstrip(';\n'))
    assert [d['id'] for d in demos]==[f'{i:02}' for i in range(1,16)]
    target=SITE/'downloads/longchang-original-physics.mp4'
    with tempfile.TemporaryDirectory() as tmp:
        listing=Path(tmp)/'clips.txt'
        listing.write_text('\n'.join("file '"+str(SITE/d['video'])+"'" for d in demos)+'\n')
        output=Path(tmp)/'physics.mp4'
        subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(output)],check=True)
        target.write_bytes(output.read_bytes())
    with zipfile.ZipFile(SITE/'downloads/longchang-physics-demonstrations.zip','w',zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('README.txt','''LongChang: scripted demonstrations of the original scene physics.

All 15 names match the current ACL scene-overview table. These prepared,
scripted demonstrations are not LLM explorations and do not contribute to
the paper's 540 evaluated runs. Original scene programs, object geometry,
mass, friction, gravity and contact laws are preserved. Setup positions and
interventions are explicit in each JSON record. Video playback is retimed;
each frame displays the original simulation time in counts.

JSON files contain 50 Hz samples, interventions, contact events and source
hashes. Videos use nearest recorded simulation samples without pose
interpolation. Camera, lighting and trajectory overlays are presentation.

Regenerate with project_page/scripts/render_physics_demos.py.
''')
        for demo in demos:
            bundle.write(SITE/demo['video'],f"videos/scene-{demo['id']}.mp4")
            bundle.write(SITE/demo['record'],f"records/scene-{demo['id']}.json")
    print(f"Packaged 15 physics demos: {sum(d['duration'] for d in demos)} seconds.")


if __name__=='__main__':main()
