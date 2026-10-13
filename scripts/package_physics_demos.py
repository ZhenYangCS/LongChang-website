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
        listing.write_text('\n'.join("file '"+str(SITE/d.get('download_video',d['video']))+"'" for d in demos)+'\n')
        output=Path(tmp)/'physics.mp4'
        subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(output)],check=True)
        target.write_bytes(output.read_bytes())
    with zipfile.ZipFile(SITE/'downloads/longchang-physics-demonstrations.zip','w',zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('README.txt','''LongChang: scripted demonstrations of the original scene physics.

All 15 names match the current ACL scene-overview table. These prepared,
scripted demonstrations are not LLM explorations and do not contribute to
the paper's 540 evaluated runs. Original scene programs, object geometry,
mass, friction, gravity and contact laws are preserved. Setup positions and
interventions are explicit in each JSON record. Each video presents one
hidden rule in a short caption. Video playback is retimed; the on-screen
clock follows the original simulation time.

JSON files contain 100 Hz samples, interventions, rule events and source
hashes. Videos use nearest recorded simulation samples without pose
interpolation. Camera, lighting and trajectory overlays are presentation.

Regenerate using project_page/scripts/render_oracle_demos.py, then
project_page/scripts/compose_plain_demos.py. The project-page README
documents the rendering workflow.
''')
        for demo in demos:
            bundle.write(SITE/demo.get('download_video',demo['video']),f"videos/scene-{demo['id']}.mp4")
            bundle.write(SITE/demo['record'],f"records/scene-{demo['id']}.json")
    print(f"Packaged 15 physics demos: {sum(d['duration'] for d in demos)} seconds.")


if __name__=='__main__':main()
