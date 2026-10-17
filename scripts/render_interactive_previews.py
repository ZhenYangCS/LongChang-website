"""Capture the actual initial native view so a first drag hits the same object.

Build-time only; the published site uses these static WebP images.
"""
import argparse
import asyncio
import io
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

SITE = Path(__file__).resolve().parents[1]


async def render(url, only=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--enable-unsafe-swiftshader'])
        page = await browser.new_page(viewport={'width':1440, 'height':960})
        await page.route('**/__interactive-preview', lambda route: route.fulfill(
            content_type='text/html', body='<style>body{margin:0}#stage{position:relative;width:1440px;height:960px;background:#f5f8f7}.room-canvas{position:absolute;inset:0;width:100%;height:100%}</style><div id="stage"></div>'))
        await page.goto(url.rstrip('/')+'/__interactive-preview')
        for key in only or [*[f'{i:02}' for i in range(1,16)], 'generate', 'mutate', 'compose']:
            await page.evaluate('''async key => {
              window.previewRoom?.destroy();
              const evolution = !/^\\d+$/.test(key),
                {createRoom} = await import('./assets/room-world.js'),
                physics = await import(evolution ? './assets/evolution-physics.js' : './assets/scene-physics.js'),
                config = await (await fetch(`data/${evolution ? 'evolution' : 'interactive-scenes'}/${key}.json`)).json(),
                simulation = await (evolution ? physics.createEvolutionSimulation : physics.createSceneSimulation)(config);
              window.previewRoom = await createRoom(document.querySelector('#stage'), () => {}, {simulation});
            }''', key)
            png = await page.locator('#stage').screenshot()
            Image.open(io.BytesIO(png)).convert('RGB').save(SITE/'assets/images'/f'interactive-room-{key}.webp', quality=90)
            print(f'Captured initial interactive view: {key}', flush=True)
        await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    parser.add_argument('--only', nargs='+', choices=[*[f'{i:02}' for i in range(1,16)], 'generate', 'mutate', 'compose'])
    args=parser.parse_args()
    asyncio.run(render(args.url,args.only))
