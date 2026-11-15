"""Browser smoke checks using an existing Chrome/Edge installation.

Run from the repository root: python backend/scripts/check_ui.py
Requires the optional playwright Python package; never downloads a browser.
"""
import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def installed_browser():
    for base in (os.environ.get('PROGRAMFILES', ''), os.environ.get('PROGRAMFILES(X86)', ''), os.environ.get('LOCALAPPDATA', '')):
        for relative in ('Google/Chrome/Application/chrome.exe', 'Microsoft/Edge/Application/msedge.exe'):
            candidate = Path(base) / relative
            if candidate.is_file():
                return str(candidate)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default=installed_browser(), help='Path to an existing Chrome or Edge executable')
    args = parser.parse_args()
    if not args.browser:
        parser.error('No installed browser found. Pass --browser; this script does not download one.')
    handler = partial(QuietHandler, directory=str(ROOT / 'backend/app/web'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    artifacts = ROOT / 'test-results'
    artifacts.mkdir(exist_ok=True)
    screenshots = ROOT / 'docs/assets'
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1080}, device_scale_factor=1, accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base, wait_until='networkidle')
            assert page.locator('#result-table tbody tr').count() == 5
            assert page.locator('#result-badge').inner_text() == 'Sample result'
            page.screenshot(path=str(screenshots / 'workspace.png'), full_page=True)
            page.get_by_role('button', name='Top customers', exact=True).click()
            page.locator('#run-query').click()
            assert 'Alex Morgan' in page.locator('#result-table').inner_text()
            page.locator('#filter-rows').fill('Singapore')
            assert page.locator('#result-table tbody tr').count() == 1
            page.locator('#filter-rows').fill('no matching row')
            assert page.locator('#empty-result').is_visible()
            page.locator('#filter-rows').fill('')
            page.locator('#table-tab').focus()
            page.keyboard.press('ArrowRight')
            assert page.locator('#sql-panel').is_visible()
            assert 'SUM(o.total_amount)' in page.locator('#sql-code').inner_text()
            with page.expect_download() as download:
                page.locator('#export-csv').click()
            download.value.save_as(artifacts / 'sample.csv')
            assert 'Alex Morgan' in (artifacts / 'sample.csv').read_text(encoding='utf-8-sig')
            page.locator('#schema').select_option('library')
            page.locator('#table-tab').click()
            assert '1984' in page.locator('#result-table').inner_text()
            page.locator('#question').fill('An arbitrary sample question')
            page.locator('#run-query').click()
            assert 'supports the suggested questions' in page.locator('#status-message').inner_text()
            assert page.locator('#result-badge').inner_text() == 'Ready'

            page.route('**/health', lambda route: route.fulfill(json={'status': 'ok', 'schemas_available': ['ecommerce', 'library'], 'live_configured': True}))
            captured = []
            def success(route):
                captured.append(route.request.post_data_json)
                route.fulfill(json={
                    'sql': "SELECT '<img src=x onerror=alert(1)>' AS product", 'success': True,
                    'attempts': 2, 'first_attempt_success': False, 'latency_ms': 1234,
                    'schema_tables_used': ['products'], 'correction_applied': True,
                    'rows': [{'product': '<img src=x onerror=alert(1)>'}, {'product': '=1+1'}],
                    'columns': ['product'], 'row_count': 2, 'error_type': None, 'error_message': None,
                })
            page.route('**/query', success)
            page.locator('#live-mode').click()
            page.wait_for_function("document.getElementById('connection').textContent.includes('API reachable')")
            page.locator('#question').fill('List products')
            page.locator('#run-query').click()
            page.wait_for_function("document.getElementById('result-badge').textContent === 'Query complete'")
            assert captured[0]['question'] == 'List products'
            assert captured[0]['max_attempts'] == 3
            assert page.locator('#result-table img').count() == 0
            assert '<img src=x' in page.locator('#result-table').inner_text()
            assert 'Correction applied' in page.locator('#result-metrics').inner_text()
            with page.expect_download() as download:
                page.locator('#export-csv').click()
            download.value.save_as(artifacts / 'escaped.csv')
            assert "'=1+1" in (artifacts / 'escaped.csv').read_text(encoding='utf-8-sig')

            page.unroute('**/query')
            page.route('**/query', lambda route: route.fulfill(status=503, json={'detail': 'The database is unavailable.'}))
            page.locator('#run-query').click()
            page.wait_for_function("document.getElementById('status-message').textContent.includes('database is unavailable')")
            assert page.locator('#export-csv').is_disabled()
            assert page.locator('#run-query').is_enabled()
            page.locator('#sample-mode').click()
            page.locator('#schema').select_option('ecommerce')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('#run-query').is_visible()
            page.locator('#mobile-schema').select_option('library')
            assert '1984' in page.locator('#result-table').inner_text()
            page.locator('#mobile-schema').select_option('ecommerce')
            page.locator('#toast').wait_for(state='hidden')
            page.screenshot(path=str(artifacts / 'workspace-mobile.png'), full_page=True)
            page.locator('#run-query').click()
            assert page.locator('#result-badge').inner_text() == 'Sample result'
            assert not errors, errors
            browser.close()
            print(json.dumps({'status': 'passed', 'checks': ['sample queries', 'schema switching', 'filters and empty state', 'keyboard tabs', 'CSV export', 'live API contract', 'HTML escaping', 'CSV formula escaping', 'API error recovery', 'mobile layout', 'no JavaScript errors'], 'screenshot': str(screenshots / 'workspace.png')}, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
