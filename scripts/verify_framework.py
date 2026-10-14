"""Check Figure 2's interactive paths, playback lifecycle and responsive layout."""
import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def packet_positions(page):
    return page.locator('.fw-edge.is-active .fw-packet').evaluate_all(
        '(dots) => dots.map(dot => [dot.getAttribute("cx"), dot.getAttribute("cy")])'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        page.evaluate('document.fonts.ready')
        flow = page.locator('#framework-flow')
        expect(flow).to_have_attribute('data-playing', 'false')
        page.locator('#fw-map').scroll_into_view_if_needed()
        expect(flow).to_have_attribute('data-playing', 'true')
        before = packet_positions(page)
        page.wait_for_timeout(180)
        assert packet_positions(page) != before, 'Active paths must carry moving packets'
        page.locator('[data-node="explorer"]').click()
        expect(flow).to_have_attribute('data-mode', 'focus')
        expect(flow).to_have_attribute('data-selection', 'explorer')
        expect(flow).to_have_attribute('data-playing', 'true')
        assert page.locator('[data-edge="record"]').get_attribute('data-from') == 'explorer'
        assert 'is-active' in page.locator('[data-edge="record"]').get_attribute('class')
        before = packet_positions(page)
        page.wait_for_timeout(180)
        assert packet_positions(page) != before, 'Inspecting a node must keep its data flowing'
        page.wait_for_timeout(4100)
        expect(flow).to_have_attribute('data-phase', '1')
        expect(flow).to_have_attribute('data-selection', 'explorer')
        page.locator('#fw-play').click()
        expect(flow).to_have_attribute('data-playing', 'false')
        before = packet_positions(page)
        page.wait_for_timeout(180)
        assert packet_positions(page) == before, 'Pause must freeze packets'
        page.locator('#fw-play').click()
        expect(flow).to_have_attribute('data-selection', 'explorer')
        expect(flow).to_have_attribute('data-playing', 'true')
        page.locator('#fw-play').click()

        # The judge receives all three inputs; the hidden law never enters the explorer.
        law = page.locator('[data-edge="law"]')
        assert law.get_attribute('data-from') == 'scenes'
        assert law.get_attribute('data-to') == 'judge'
        assert page.locator('[data-edge="evidence"]').get_attribute('data-from') == 'traces'
        page.locator('[data-node="judge"]').click()
        assert all(word in page.locator('#fw-detail-input').inner_text().lower()
                   for word in ['law', 'report', 'traces'])
        assert 'is-active' in law.get_attribute('class')
        assert 'is-active' not in page.locator('[data-node="explorer"]').get_attribute('class')

        # Native button activation and stage navigation work without a pointer.
        page.locator('[data-node="tools"]').focus()
        page.keyboard.press('Enter')
        expect(flow).to_have_attribute('data-selection', 'tools')
        assert 'apparatus' in page.locator('#fw-detail-description').inner_text()
        page.locator('[data-fw-stage="1"]').focus()
        page.keyboard.press('ArrowRight')
        expect(flow).to_have_attribute('data-phase', '2')
        page.keyboard.press('End')
        expect(flow).to_have_attribute('data-phase', '4')
        assert 'is-active' in page.locator('[data-edge="feedback"]').get_attribute('class')
        assert 'is-active' in page.locator('[data-edge="evolve"]').get_attribute('class')

        # Autoplay advances, and resumes from its frozen position after leaving the viewport.
        page.locator('#fw-reset').click()
        expect(flow).to_have_attribute('data-phase', '0')
        expect(flow).to_have_attribute('data-mode', 'cycle')
        page.locator('#fw-play').click()
        expect(flow).to_have_attribute('data-phase', '1', timeout=8500)
        page.evaluate('window.scrollTo({top: 0, behavior: "instant"})')
        expect(flow).to_have_attribute('data-playing', 'false')
        before = packet_positions(page)
        page.wait_for_timeout(180)
        assert packet_positions(page) == before, 'Offscreen animation must stop'
        page.locator('#fw-map').scroll_into_view_if_needed()
        expect(flow).to_have_attribute('data-playing', 'true')
        page.evaluate('document.querySelector("#motion-dialog").showModal()')
        expect(flow).to_have_attribute('data-playing', 'false')
        page.evaluate('document.querySelector("#motion-dialog").close()')
        expect(flow).to_have_attribute('data-playing', 'true')
        page.evaluate('document.querySelector("#result-evidence-dialog").showModal()')
        expect(flow).to_have_attribute('data-playing', 'false')
        page.evaluate('document.querySelector("#result-evidence-dialog").close()')
        expect(flow).to_have_attribute('data-playing', 'true')
        page.locator('[data-fw-stage="3"]').click()

        # Paths stay inside the diagram after relayout, and every arrow ends on
        # its declared target's boundary, including the stacked mobile version.
        for width in [1440, 1280, 1024, 960, 901, 900, 768, 390, 360, 320]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.wait_for_timeout(100)
            problems = page.evaluate('''() => {
                const map = document.querySelector('#fw-map').getBoundingClientRect();
                const problems = [];
                const textBoxes = [];
                document.querySelectorAll('.fw-node,.fw-lane-title').forEach(node => {
                    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        if (!walker.currentNode.textContent.trim()) continue;
                        const range = document.createRange();
                        range.selectNodeContents(walker.currentNode);
                        for (const box of range.getClientRects()) {
                            if (box.width) textBoxes.push({box, name:walker.currentNode.textContent});
                        }
                    }
                });
                const labels = [...document.querySelectorAll('.fw-edge-label text')]
                    .map(text => ({box:text.getBoundingClientRect(), name:text.textContent}))
                    .filter(label => label.box.width);
                const overlaps = (a,b,gap) => a.left < b.right+gap && a.right > b.left-gap && a.top < b.bottom+gap && a.bottom > b.top-gap;
                labels.forEach((label,index) => {
                    if (textBoxes.some(text => overlaps(label.box,text.box,3)))
                        problems.push('label overlaps node or heading: '+label.name);
                    if (labels.slice(index+1).some(other => overlaps(label.box,other.box,3)))
                        problems.push('labels overlap: '+label.name);
                });
                const detail = document.querySelector('#fw-detail').getBoundingClientRect();
                const stages = document.querySelector('.fw-stages').getBoundingClientRect();
                if (detail.top < stages.bottom || detail.bottom > map.top)
                    problems.push('step summary must sit between navigation and diagram');
                const lawLabel = document.querySelector('[data-edge="law"] .fw-edge-label').getBoundingClientRect();
                const judgeBox = document.querySelector('[data-node="judge"]').getBoundingClientRect();
                const evaluationBox = document.querySelector('.fw-evaluation').getBoundingClientRect();
                if (!lawLabel.width || lawLabel.left < evaluationBox.left || lawLabel.top < evaluationBox.top || lawLabel.bottom > judgeBox.top)
                    problems.push('hidden-law label must stay beside the judge input');
                const protectedText = [...textBoxes, ...labels];
                if (document.documentElement.scrollWidth > innerWidth) problems.push('page overflow');
                document.querySelectorAll('.fw-node').forEach(node => {
                    if (node.scrollWidth > node.clientWidth) problems.push('text overflow: '+node.dataset.node);
                });
                document.querySelectorAll('.fw-edge').forEach(edge => {
                    const path = edge.querySelector('path'), length = path.getTotalLength();
                    const end = path.getPointAtLength(length);
                    const node = document.querySelector('[data-node="'+edge.dataset.to+'"]').getBoundingClientRect();
                    const x = end.x+map.left, y = end.y+map.top;
                    const inside = x >= node.left-1 && x <= node.right+1 && y >= node.top-1 && y <= node.bottom+1;
                    const boundary = Math.min(Math.abs(x-node.left), Math.abs(x-node.right), Math.abs(y-node.top), Math.abs(y-node.bottom)) < 1;
                    if (!inside || !boundary) problems.push('detached arrow: '+edge.dataset.edge);
                    for (let distance = 0; distance <= length; distance += 2) {
                        const point = path.getPointAtLength(distance);
                        if (point.x < 0 || point.x > map.width || point.y < 0 || point.y > map.height)
                            problems.push('path outside map: '+edge.dataset.edge);
                        const px = point.x+map.left, py = point.y+map.top;
                        const obstruction = protectedText.find(({box}) => px > box.left-5 && px < box.right+5 && py > box.top-5 && py < box.bottom+5);
                        if (obstruction) {
                            problems.push('flow crosses text: '+edge.dataset.edge+' / '+obstruction.name);
                            break;
                        }
                    }
                });
                return problems;
            }''')
            assert not problems, (width, problems)
            if args.screenshots and width in [1440, 1024, 390]:
                flow.screenshot(path=str(args.screenshots / f'framework-{width}.png'))

        reduced = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        reduced.on('pageerror', lambda error: errors.append(str(error)))
        reduced.goto(args.url, wait_until='domcontentloaded')
        reduced.locator('#fw-map').scroll_into_view_if_needed()
        expect(reduced.locator('#framework-flow')).to_have_attribute('data-playing', 'false')
        before = packet_positions(reduced)
        reduced.wait_for_timeout(180)
        assert packet_positions(reduced) == before
        reduced.locator('#fw-play').click()
        expect(reduced.locator('#framework-flow')).to_have_attribute('data-playing', 'true')
        browser.close()
    assert not errors, errors
    print('PASS: actual packet motion, pause/resume, automatic stages, offscreen and modal lifecycle.')
    print('PASS: selected flows keep moving without changing stage; all turns record directly from exploration.')
    print('PASS: judge input routing, keyboard controls, reduced motion.')
    print('PASS: 320–1440 px text layout, paths within the map, every arrow attached to its target.')
    print('PASS: all flow paths clear labels, node text and headings, including particle clearance.')
    print('PASS: no JavaScript errors.')


if __name__ == '__main__':
    main()
