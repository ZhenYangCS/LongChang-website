"""Verify the full public audit trail and the report browser."""
import argparse
import csv
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from verify_result_archive import verify as verify_archive

SITE = Path(__file__).resolve().parents[1]
ROOT = SITE.parent
DATA = SITE/'data/result-evidence'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    source_path = ROOT/'ACL/non_submission/materials/results/sources/gpt_6_1_sol_episodes.csv'
    with source_path.open() as stream:
        source = {row['episode_id']:row for row in csv.DictReader(stream)}
    manifest = json.loads((DATA/'manifest.json').read_text())
    english_download = json.loads((SITE/'downloads/longchang-judge-summaries-en.json').read_text())
    english_summaries = {entry['episode_id']:entry for entry in english_download['runs']}
    assert len(english_summaries) == 540
    assert manifest['source_sha256'] == hashlib.sha256(source_path.read_bytes()).hexdigest()
    paper = json.loads((SITE/'data/paper.js').read_text().removeprefix('window.LONGCHANG = ').rstrip(';\n'))
    models = {model['name']:model for model in paper['models']}
    seen = set()
    turns = 0
    for path in manifest['paths']:
        group = json.loads((DATA/path).read_text())
        assert [run['repeat'] for run in group['runs']] == [1,2,3]
        for run in group['runs']:
            row = source[run['id']]
            summary = english_summaries[run['id']]
            assert summary['evaluation_sha256'] == run['evaluation_sha256']
            assert summary['reason_sha256'] == hashlib.sha256(run['reason'].encode()).hexdigest()
            assert (summary['D'], summary['C'], summary['S']) == (run['D'], run['C'], run['S'])
            assert run['id'] not in seen
            seen.add(run['id'])
            assert row['scene'][:2] == group['scene']
            assert row['model'].lower() == group['model'].lower()
            assert run['session_sha256'] == row['session_sha256']
            assert run['evaluation_sha256'] == row['eval_sha256']
            assert run['C'] == (row['correct'] == 'True')
            if run['control']:
                assert run['D'] is None and run['S'] is None
                assert run['accepted'] == run['C']
            else:
                assert run['S'] == (row['supported'] == 'True')
                assert run['D'] == (row['success'] == 'True') == (run['C'] and run['S'])
            payload = gzip.decompress((SITE/run['record']).read_bytes())
            assert hashlib.sha256(payload).hexdigest() == run['record_sha256']
            record = json.loads(payload)
            assert record['episode_id'] == run['id']
            assert len(record['turns']) == run['turn_count']
            actual = {turn['turn'] for turn in record['turns']}
            assert len(actual) == len(record['turns'])
            for claim in run['report']['conclusions']:
                assert set(claim['evidence_turns']) <= actual
            turns += len(record['turns'])
            # Exact report and original feedback remain available, with no
            # synthesized findings or model observations used as environment data.
            session_folder = ROOT/'runs/main-15-20260930-022640-2180080'/row['scene']
            model_folder = next(folder for folder in session_folder.iterdir() if folder.name.lower() == row['model'].lower())
            session = json.loads((model_folder/f'r{row["repeat"]}'/'T0/session.json').read_text())
            assert record['report'] == session['report']
            fields = ('turn','note','act','outcome','observation','result_observation','raw')
            assert record['turns'] == [{key:turn.get(key) for key in fields} for turn in session['turns']]
            evaluation_path = Path(row['eval_path'])
            if not evaluation_path.is_absolute(): evaluation_path = ROOT/evaluation_path
            evaluation = json.loads(evaluation_path.read_text())
            assert run['reason'] == evaluation['judgement']['reason']
        model = models[group['model']]
        if group['scene'] == '01':
            assert sum(not run['accepted'] for run in group['runs']) == model['R']
        else:
            for key in ['D','C','S']:
                assert sum(run[key] for run in group['runs']) == model['scenes'][group['scene']][key]
    assert len(seen) == 540 and len(manifest['paths']) == 180 and turns == 30223
    print('PASS: all 540 reports, 30,223 original turns and verdicts match the source; all D/C/S and control aggregates match the paper.', flush=True)
    archive_path = SITE/manifest['archive']['path']
    assert archive_path.stat().st_size == manifest['archive']['bytes']
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == manifest['archive']['sha256']
    with zipfile.ZipFile(archive_path) as archive:
        verify_archive(archive.read)
        index = json.loads(archive.read('manifest.json'))
        assert index['source_index_sha256'] == manifest['source_sha256']
        assert {run['episode_id'] for run in index['runs']} == seen
        assert len(archive.namelist()) == 1083
        assert archive.read('verify.py') == (SITE/'scripts/verify_result_archive.py').read_bytes()
    for path in manifest['paths']:
        group = json.loads((DATA/path).read_text())
        for run in group['runs']:
            with zipfile.ZipFile(SITE/run['archive']) as archive:
                assert hashlib.sha256(archive.read('session.json')).hexdigest() == run['session_sha256']
                assert hashlib.sha256(archive.read('evaluation.json')).hexdigest() == run['evaluation_sha256']
                entry = json.loads(archive.read('manifest.json'))['runs'][0]
                assert entry['episode_id'] == run['id']
                assert entry['session_file'] == 'session.json' and entry['evaluation_file'] == 'evaluation.json'
    print('PASS: full-study archive and all 540 individual ZIPs contain the exact original JSON files and portable manifests.', flush=True)

    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>r.name.includes("/result-evidence/"))')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>r.name.includes("/judge-summaries/"))')
        assert not page.evaluate('performance.getEntriesByType("resource").some(r=>r.name.includes("/result-json/")||r.name.endsWith("longchang-main-study-json.zip"))')
        assert page.locator('#evidence-provenance').count() == 0
        assert page.locator('#results-json-download').get_attribute('href') == manifest['archive']['path']
        assert page.locator('#results-summary-download').get_attribute('href') == 'downloads/longchang-judge-summaries-en.json'
        assert page.locator('#model-chart .result-lane:visible').count() == 12
        assert page.locator('#model-chart [data-result-metric="D"]').count() == 12
        assert page.locator('[data-result-view]').count() == 0
        assert page.locator('.result-model-name').all_text_contents() == list(models)
        for name in models:
            page.locator(f'[data-model="{name}"]').click()
            assert page.locator('.result-scene').count() == 14
            assert page.locator('[data-result-scene]').count() == 15
            for scene, counts in models[name]['scenes'].items():
                assert page.locator(f'.result-scene[data-result-scene="{scene}"] strong').all_text_contents() == [f'{counts[key]}/3' for key in ['D','C','S']]
        for model,scene in [('GPT-6-Astra','02'),('Claude-Opus-5','06'),('MiMo-V2.6-Pro','04'),('DeepSeek-Flash','15'),('GPT-6-Astra','07'),('GPT-6-Astra','01')]:
            page.locator(f'[data-model="{model}"]').click()
            page.locator(f'[data-result-scene="{scene}"]').click()
            expect(page.locator('#evidence-content')).to_be_visible()
            group = json.loads((DATA/model.lower()/f'{scene}.json').read_text())
            assert page.locator('#evidence-runs button').count() == 3
            assert page.locator('#evidence-views button').all_text_contents() == ['Summary','Full report']
            expect(page.locator('#evidence-summary-view')).to_be_visible()
            expect(page.locator('#evidence-full-view')).not_to_be_visible()
            for i, run in enumerate(group['runs']):
                page.locator(f'#evidence-run-{run["repeat"]}').click()
                expect(page.locator('#result-evidence-dialog')).to_have_attribute('data-run', str(run['repeat']))
                assert page.locator('#evidence-record-download').get_attribute('href') == run['archive']
                page.locator('#evidence-summary-tab').click()
                expect(page.locator('#evidence-summary')).to_have_text(english_summaries[run['id']]['summary'])
                assert page.locator('#evidence-summary').get_attribute('lang') == 'en'
                assert page.locator('.evidence-claim-text:visible').count() == 0
                assert page.locator('#result-evidence-dialog details').count() == 0
                page.locator('#evidence-full-tab').click()
                assert page.locator('.evidence-claim-text').all_text_contents() == [claim['claim'] for claim in run['report']['conclusions']]
                assert page.locator('.evidence-claim-text:visible').count() == len(run['report']['conclusions'])
                assert page.locator('.evidence-experiment').count() == len(run['report']['experiments'])
                assert page.locator('#evidence-reason').inner_text() == run['reason']
                if not run['control']:
                    assert page.locator(f'#evidence-run-{run["repeat"]}').evaluate('(b)=>[b.dataset.d,b.dataset.c,b.dataset.s]') == [str(run[key]).lower() for key in ['D','C','S']]
                if i == 0 and run['report']['conclusions']:
                    number = run['report']['conclusions'][0]['evidence_turns'][0]
                    page.locator(f'[data-evidence-turn="{number}"]').first.click()
                    expect(page.locator('#evidence-turn-content')).to_be_visible(timeout=15000)
                    record = json.loads(gzip.decompress((SITE/run['record']).read_bytes()))
                    turn = next(turn for turn in record['turns'] if turn['turn'] == number)
                    if turn['act']: assert page.locator('#evidence-turn-action').inner_text() == turn['act']
                    assert json.loads(page.locator('#evidence-turn-after').inner_text()) == turn['result_observation']
                    assert page.locator('#evidence-turn-select option').count() == run['turn_count']
                    page.keyboard.press('Escape')
                    expect(page.locator('#evidence-turn-dialog')).not_to_be_visible()
            if scene == '07':
                expect(page.locator('#evidence-film')).to_be_visible()
                page.locator('#evidence-film').click()
                expect(page.locator('#exploration-dialog')).to_be_visible()
                expect(page.locator('#discovery-title')).to_have_text('Tile rebounds')
                page.keyboard.press('Escape')
                expect(page.locator('#result-evidence-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#result-evidence-dialog')).not_to_be_visible()
        page.locator('[data-model="GPT-6-Astra"]').click()
        page.locator('[data-result-scene="07"]').click()
        page.locator('#evidence-run-3').click()
        with page.expect_download() as download:
            page.locator('#evidence-record-download').click()
        assert download.value.suggested_filename == 'GPT-6-Astra-scene-07-run-3.zip'
        with zipfile.ZipFile(download.value.path()) as archive:
            verify_archive(archive.read)
        page.keyboard.press('Escape')
        print('PASS: D-only chart in paper order, all model/scene counts, two reading modes, complete findings and experiments, English summaries and original citations, normal controls and exact-run film links.', flush=True)
        page.route('**/result-evidence/qwen3-max/03.json', lambda route: route.fulfill(status=503,body='unavailable'))
        page.evaluate('showResultEvidence("Qwen3-Max","03")')
        expect(page.locator('#evidence-retry')).to_be_visible()
        page.unroute('**/result-evidence/qwen3-max/03.json')
        page.locator('#evidence-retry').click()
        expect(page.locator('#evidence-content')).to_be_visible()
        page.keyboard.press('Escape')
        for width in [1440,1024,768,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            page.locator('[data-model="GPT-6-Astra"]').click()
            page.locator('[data-result-scene="02"]').click()
            expect(page.locator('#evidence-content')).to_be_visible()
            assert page.locator('#result-evidence-dialog').evaluate('e=>e.scrollWidth<=e.clientWidth')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#evidence-run-1').focus()
            page.keyboard.press('End')
            expect(page.locator('#result-evidence-dialog')).to_have_attribute('data-run','3')
            page.keyboard.press('Escape')
        browser.close()
    assert not errors, errors
    print('PASS: lazy loading, retry, keyboard controls, 320–1440 px layout and no JavaScript errors.')


if __name__ == '__main__':
    main()
