
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

TARGET_DATE = "2026-03-25"
base = Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic")
outfile = base / "memory" / "eeworld-source-code" / "2026-3-25-2026-3-27.json"
old_files = [
    base / "memory" / "eeworld-source-code" / "2026-03-27T11-09-11Z-latest-day-2026-03-25.json",
    base / "memory" / "eeworld-source-code" / "2026-03-27T11-21-00Z-latest-day-2026-03-25.json",
    base / "memory" / "eeworld-source-code" / "2026-03-27T19-15-00+08-00-latest-day-2026-03-25.json",
]

categoryCounts = {
    '????': 2,'????': 2,'????': 3,'??': 2,'????': 1,'????': 1,
    '?????': 2,'????': 2,'???': 4,'????/??': 2,'??/????': 2,'???/MCU': 6
}
keywordCounts = {
    '800V DC ????': 1,'AI ????': 1,'GPU??': 1,'????': 1,'????': 1,
    '??AI MCU': 1,'TinyEngine NPU': 1,'????': 1,'????': 1,'?????': 1,
    '??ECU SoC': 1,'ASIL D': 1,'AI????': 1,'??????': 1,'????': 1,
    '4D???????': 1,'????': 1,'MIMO': 1,'????': 1,'????': 1,
    '????????': 1,'????': 1,'??????': 1,'???????': 1,'??????': 1,
    'i.MX93 SoC': 1,'IW610': 1,'SiP????': 1,'??????': 1,'??AI???': 1,
    '?????': 1,'??????': 1,'??????': 1,'??????': 1,'????????': 1,
    '???????': 1,'???????': 1,'???????': 1,'INL?0.02?': 1,'????????': 1,
    '3nm FinFET': 1,'???TCAM': 1,'????': 1,'ECC??': 1,'??????': 1,
    'ECU????': 1,'?/???': 1,'????': 1,'???': 1,'????': 2,
    '????': 1,'gPTP/TSN': 1,'??????': 1,'????': 1,'?????': 1,
    'TPM': 1,'FPGA???': 1,'????': 1,'???????': 1,
    '??AI': 1,'??????': 1,'????': 1,'?????': 1,'????????': 1,
    '??AI????': 1,'???????': 1,'AI SDK/???': 1,'Zephyr??': 1,'?????????': 1,
    '??????': 1,'D?????': 1,'32V??': 1,'2?110W??': 1,'??TPA3116??': 1,
    'SiC????': 1,'HV-H3TRB': 1,'AlN/Al2O3??': 1,'TIM???': 1,'???????': 1,
    '???????': 3,'??????': 3,'??????': 3,'T2PAK': 2,'???': 3,'TIM': 3,'???': 2,'???????': 2,'????????IC': 2,'LX4580': 2,'??MCU': 3,'????': 2,'RA8 MCU': 2
}
categoryAliases = {
    '????': ['????','??','wi-fi','wifi','ble','bluetooth','802.15.4','uwb','?????','RF??'],
    '??': ['??','rf','???','??','??','RF??'],
    '????/??': ['??','????','????','????'],
    '??/????': ['???','?????','?????','???????'],
    '???/MCU': ['?????/MCU','PIC???','STM32','?????','??????']
}
keywordAliases = {
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

def token_in_text(token, text):
    t = (token or '').strip().lower()
    if not t:
        return False
    return t in text

def score_item(it):
    hay = f"{it['title']} {it['category']} {it['url']}".lower()
    score = 0.0
    mc = []
    mk = []
    for cat, cnt in categoryCounts.items():
        if it['category'] == cat or it['category'] in categoryAliases.get(cat, []):
            score += 3 * int(cnt or 1)
            mc.append(cat)
    for kw, cnt in keywordCounts.items():
        hit = token_in_text(kw, hay)
        if not hit:
            for alias in keywordAliases.get(kw, []):
                if token_in_text(alias, hay):
                    hit = True
                    break
        if hit:
            score += 1.2 * int(cnt or 1)
            mk.append(kw)
    mc.sort(key=lambda x: (-(categoryCounts.get(x, 0)), x))
    mk.sort(key=lambda x: (-(keywordCounts.get(x, 0)), x))
    out = dict(it)
    out['score'] = round(score, 2)
    out['matched_categories'] = mc
    out['matched_keywords'] = mk
    return out

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    all_items = []
    fetched_pages = []
    for pg in range(1, 20):
        url = f'https://www.eeworld.com.cn/latestnews/{pg}' if pg > 1 else 'https://www.eeworld.com.cn/latestnews'
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
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
        dates = sorted({r['date'] for r in rows if r.get('date')})
        fetched_pages.append({'page': pg, 'url': url.replace('https://','http://'), 'item_count': len(rows), 'dates': dates})
        for r in rows:
            if r.get('date') == TARGET_DATE:
                all_items.append(r)
        if dates and dates[0] < TARGET_DATE:
            break
    browser.close()

seen = set()
dedup = []
for it in all_items:
    if it['url'] in seen:
        continue
    seen.add(it['url'])
    dedup.append(it)

ranked = [score_item(x) for x in dedup]
ranked.sort(key=lambda x: (-x['score'], x['title']))

# merge with old files by url, keeping richer existing fields if any
merged = {}
for path in old_files:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            for item in data.get('ranked', []):
                if isinstance(item, dict) and item.get('url'):
                    merged[item['url']] = item
        except Exception:
            pass
for item in ranked:
    merged[item['url']] = item
final_ranked = list(merged.values())
final_ranked = [x for x in final_ranked if x.get('date') == TARGET_DATE]
final_ranked.sort(key=lambda x: (-float(x.get('score', 0)), x.get('title','')))

payload = {
    'mode': 'latest-day',
    'source': 'http://www.eeworld.com.cn/latestnews',
    'dates': [TARGET_DATE],
    'fetched_at': '2026-03-27T11:37:00+00:00',
    'max_pages': 20,
    'profile': 'memory/eeworld-reading-profile.json',
    'total_items': len(final_ranked),
    'ranked': final_ranked,
    'fetched_pages': fetched_pages
}
outfile.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(str(outfile))
print(f'total_items={len(final_ranked)}')
