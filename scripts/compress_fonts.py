"""Create WOFF2 copies of the local TTF fonts without subsetting glyphs.

Optional maintenance dependency: fonttools[woff]. Originals remain available
for figure exporters; publishing the prebuilt website does not run this script.
"""
from pathlib import Path
from fontTools.ttLib import TTFont

fonts = Path(__file__).resolve().parents[1] / 'assets/fonts'
for source in sorted(fonts.glob('*.ttf')):
    with TTFont(source, recalcTimestamp=False) as font:
        font.flavor = 'woff2'
        target = source.with_suffix('.woff2')
        font.save(target)
        print(f'{source.name}: {source.stat().st_size} → {target.stat().st_size} bytes')
