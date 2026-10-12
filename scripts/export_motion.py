"""Export deterministic browser illustrations as portable MP4 and GIF files.

Requires Playwright/Chromium and ffmpeg (or imageio-ffmpeg). No API calls,
MuJoCo simulation, or experimental records are generated or changed.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1]


def encode(page, ffmpeg, output, seconds, fps, draw):
    temporary = output.with_name(output.stem + '.partial.mp4')
    with tempfile.TemporaryFile() as errors:
        command = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
                   '-f', 'image2pipe', '-framerate', str(fps), '-vcodec', 'png', '-i', '-',
                   '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
                   '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                   '-metadata', 'title=LongChang — Illustrations of physical laws',
                   '-metadata', 'artist=Anonymous Authors', str(temporary)]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
        try:
            for frame in range(seconds * fps):
                draw(frame / fps)
                process.stdin.write(page.screenshot(animations='disabled'))
                if frame % (8 * fps) == 0:
                    print(f'{output.name}: {frame // fps}/{seconds} seconds', flush=True)
            process.stdin.close()
            code = process.wait()
            if code:
                errors.seek(0)
                raise RuntimeError(errors.read().decode())
            temporary.replace(output)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg')
    parser.add_argument('--fps', type=int, default=20)
    parser.add_argument('--only', choices=['atlas', 'overview', 'gifs'])
    args = parser.parse_args()
    ffmpeg = args.ffmpeg or shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    target = SITE / 'downloads'
    frames = target / 'animated-scenes'
    frames.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--no-sandbox'])
        for mode in ['atlas', 'overview']:
            if args.only and args.only != mode:
                continue
            page = browser.new_page(viewport={'width':1280, 'height':720}, reduced_motion='reduce')
            page.goto((SITE / 'index.html').as_uri())
            page.evaluate('document.fonts.ready')
            if mode == 'atlas':
                def draw(t):
                    page.evaluate('([id,t])=>LongChangAtlas.renderFrame(id,t)', [f'{int(t // 8) + 1:02}', t % 8])
                encode(page, ffmpeg, target / 'longchang-15-worlds.mp4', 120, args.fps, draw)
            else:
                encode(page, ffmpeg, target / 'longchang-motion-atlas.mp4', 48, args.fps,
                       lambda t:page.evaluate('(t)=>LongChangMotion.renderFrame(t)', t))
            page.close()
        browser.close()
    if args.only not in ['atlas', 'overview']:
        for number in range(1, 16):
            output = frames / f'scene-{number:02}.gif'
            subprocess.run([ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
                            '-ss', str((number - 1) * 8), '-t', '8',
                            '-i', str(target / 'longchang-15-worlds.mp4'),
                            '-vf', 'fps=12,scale=768:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
                            '-loop', '0', str(output)], check=True)
            print(f'Exported {output.name}', flush=True)
        readme = """LongChang — Fifteen physical-law illustrations

These are idealized illustrations of the laws described in the paper, not
recorded MuJoCo experiments or evidence of model discovery. Each GIF uses
the scene's default interactive setting and lasts eight seconds.

The site offers alternate experiment settings, full law descriptions,
recorded initial worlds, and separate verified model-exploration videos.
Ordinary physics is simplified or omitted as stated in each figure.
Playback time is not simulation time; timing rules are labelled in counts.

Source: project_page/assets/atlas.js and data/paper.js.
Regenerate: python scripts/export_motion.py
"""
        for filename, selected in [('longchang-15-worlds-gifs.zip', range(1, 16)),
                                   ('longchang-animated-figures.zip', [7, 6, 14, 15])]:
            with zipfile.ZipFile(target / filename, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('README.txt', readme)
                for number in selected:
                    path = frames / f'scene-{number:02}.gif'
                    archive.write(path, path.name)
        (frames / 'manifest.json').write_text(json.dumps({
            'kind':'idealized law illustrations', 'duration_seconds':8,
            'files':[f'scene-{i:02}.gif' for i in range(1, 16)]}, indent=2) + '\n')
    print('Motion exports complete.', flush=True)


if __name__ == '__main__':
    main()
