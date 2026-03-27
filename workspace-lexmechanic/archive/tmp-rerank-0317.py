import json, pathlib, re
src = pathlib.Path(r'C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\eeworld-source-code\2026-03-19T14-39-21Z-latest-day-2026-03-17.json')
prof = pathlib.Path(r'C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\eeworld-reading-profile.json')
data = json.loads(src.read_text(encoding='utf-8'))
profile = json.loads(prof.read_text(encoding='utf-8'))
cat_counts = profile.get('category_counts', {})
kw_counts = profile.get('keyword_counts', {})
cat_alias = {
    '车用传感器/MCU': '传感器/MCU',
    '网络通信': '无线传输',
    '工业电子': '工业控制',
    '驱动': '功率器件/封装',
    'FPGA/DSP': '嵌入式系统',
}
kw_aliases = {
    '射频': ['rf', '无线', '毫米波', '雷达'],
    'DSP': ['fpga/dsp', '信号处理'],
    '嵌入式系统': ['嵌入式', 'mcu', '单片机'],
    '车用传感器': ['传感器', '毫米波雷达', '激光雷达'],
}
def token_in_text(token, text):
    t = token.strip().lower()
    if not t:
        return False
    if re.fullmatch(r'[a-z0-9][a-z0-9_\-/+\.]*', t):
        return bool(re.search(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])', text.lower()))
    return t in text.lower()
for item in data['ranked']:
    category = str(item.get('category', '')).strip()
    mapped = cat_alias.get(category, category)
    score = 0.0
    mc = []
    mk = []
    if mapped in cat_counts:
        score += 3.0 * int(cat_counts[mapped])
        mc.append(mapped)
    hay = (str(item.get('title','')) + ' ' + category + ' ' + str(item.get('url',''))).lower()
    for kw, cnt in kw_counts.items():
        direct = token_in_text(str(kw), hay)
        alias_hit = False
        if not direct:
            for a in kw_aliases.get(str(kw), []):
                if token_in_text(a, hay):
                    alias_hit = True
                    break
        if direct:
            score += 1.2 * int(cnt)
            mk.append(str(kw))
        elif alias_hit:
            score += 0.8 * int(cnt)
            mk.append(str(kw))
    item['new_score'] = round(score, 2)
    item['matched_categories'] = mc
    item['matched_keywords_new'] = mk
ranked = sorted(data['ranked'], key=lambda x: (float(x.get('new_score', 0.0)), str(x.get('date','')), str(x.get('title',''))), reverse=True)
for i, it in enumerate(ranked[:12], 1):
    print(str(i) + '. [' + format(it['new_score'], '.2f') + '] [' + str(it.get('category')) + '] ' + str(it.get('title')))
    print('   分类命中: ' + ('、'.join(it.get('matched_categories', [])) if it.get('matched_categories') else '(无)'))
    print('   关键词命中: ' + ('、'.join(it.get('matched_keywords_new', [])[:6]) if it.get('matched_keywords_new') else '(无)'))
    print('   ' + str(it.get('url')))
