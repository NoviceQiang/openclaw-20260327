
import argparse, json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

CATEGORY_ALIASES = {
    '????': ['????','??','wi-fi','wifi','ble','bluetooth','802.15.4','uwb','?????','RF??'],
    '??': ['??','rf','???','??','??','RF??'],
    '????/??': ['??','????','????','????'],
    '??/????': ['???','?????','?????','???????'],
    '???/MCU': ['?????/MCU','PIC???','STM32','?????','??????']
}
KEYWORD_ALIASES = {
    '??': ['rf','??','???'],
    '??AI MCU': ['mcu','?? ai','??AI','tinyml'],
    '??MCU': ['mcu','sam9x75','stm32','???'],
    '??????': ['????','????','?????','pmu','adc'],
    '???????': ['pmu','adc','????','????','?????','?????'],
    '??????': ['????','top-side cooling','q-dpak','t2pak'],
    '???': ['???','??','tim','???'],
    'TIM': ['tim','???'],
    '???????': ['???','layout'],
    '????': ['????','????'],
    'RA8 MCU': ['ra8','renesas'],
    '????????IC': ['???','????']
}

def score_item(item, category_counts, keyword_counts):
    hay = f"{item.get('title','')} {item.get('category','')} {item.get('url','')}".lower()
    score = 0.0
    matched_categories = []
    matched_keywords = []

    for cat, cnt in category_counts.items():
        if item.get('category') == cat or item.get('category') in CATEGORY_ALIASES.get(cat, []):
            score += 3 * int(cnt or 1)
            matched_categories.append(cat)

    for kw, cnt in keyword_counts.items():
        q = (kw or '').strip().lower()
        hit = bool(q and q in hay)
        if not hit:
            for alias in KEYWORD_ALIASES.get(kw, []):
                a = (alias or '').strip().lower()
                if a and a in hay:
                    hit = True
                    break
        if hit:
            score += 1.2 * int(cnt or 1)
            matched_keywords.append(kw)

    matched_categories.sort(key=lambda x: (-(category_counts.get(x, 0)), x))
    matched_keywords.sort(key=lambda x: (-(keyword_counts.get(x, 0)), x))

    out = dict(item)
    out['score'] = round(score, 2)
    out['matched_categories'] = matched_categories
    out['matched_keywords'] = matched_keywords
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--max-pages', type=int, default=20)
    args = ap.parse_args()

    target_date = args.date
    root = Path(r'C:\Users\Qiang\.openclaw\workspace-lexmechanic')
    source_dir = root / 'memory' / 'eeworld-source-code'
    profile_path = root / 'memory' / 'eeworld-reading-profile.json'

    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    category_counts = profile.get('category_counts', {})
    keyword_counts = profile.get('keyword_counts', {})

    now = datetime.now()
    ty, tm, td = [int(x) for x in target_date.split('-')]
    file_name = f"{ty}-{tm}-{td}-{now.year}-{now.month}-{now.day}.json"
    out_path = source_dir / file_name

    all_items = []
    fetched_pages = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for pg in range(1, args.max_pages + 1):
            url = f'https://www.eeworld.com.cn/latestnews/{pg}' if pg > 1 else 'https://www.eeworld.com.cn/latestnews'
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            try:
                page.wait_for_selector('li h3', timeout=5000)
            except Exception:
                pass

            rows = page.locator('li h3').evaluate_all("""
            els => els.map(h3 => {
              const links = h3.querySelectorAll('a');
              const categoryEl = links[0];
              const titleEl = links[1] || links[0];
              const txt = h3.textContent || '';
              const m = txt.match(/(20\\d{2}-\\d{2}-\\d{2})\\s*$/);
              const toAbs = href => { try { return new URL(href, location.origin).href; } catch { return href || ''; } };
              return {
                category: (categoryEl?.textContent || '').trim().replace(/^\\[|\\]$/g,''),
                category_url: toAbs(categoryEl?.getAttribute('href') || ''),
                title: (titleEl?.textContent || '').trim(),
                url: toAbs(titleEl?.getAttribute('href') || ''),
                date: m ? m[1] : ''
              };
            }).filter(x => x.title && x.url)
            """)

            dates = sorted({x.get('date') for x in rows if x.get('date')})
            fetched_pages.append({
                'page': pg,
                'url': url.replace('https://', 'http://'),
                'item_count': len(rows),
                'dates': dates
            })

            page_target = [x for x in rows if x.get('date') == target_date]
            all_items.extend(page_target)

            if dates and dates[0] < target_date:
                break

        browser.close()

    # merge by url with existing same-name file if present
    merged = {}
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding='utf-8'))
            for it in old.get('ranked', []):
                if isinstance(it, dict) and it.get('url'):
                    merged[it['url']] = it
        except Exception:
            pass

    for it in all_items:
        if it.get('url'):
            merged[it['url']] = score_item(it, category_counts, keyword_counts)

    ranked = [v for v in merged.values() if v.get('date') == target_date]
    ranked.sort(key=lambda x: (-float(x.get('score', 0)), x.get('title', '')))

    payload = {
        'mode': 'latest-day',
        'source': 'http://www.eeworld.com.cn/latestnews',
        'dates': [target_date],
        'fetched_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'max_pages': args.max_pages,
        'profile': 'memory/eeworld-reading-profile.json',
        'total_items': len(ranked),
        'ranked': ranked,
        'fetched_pages': fetched_pages
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(str(out_path))
    print(f'total_items={len(ranked)}')
    print('pages=' + ','.join(str(x['page']) for x in fetched_pages))

if __name__ == '__main__':
    main()
