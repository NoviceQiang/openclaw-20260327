import re, pathlib, collections, json
root=pathlib.Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\interests")
files=[root/f"2026-03-{d:02d}.md" for d in range(23,30) if (root/f"2026-03-{d:02d}.md").exists()]
entries=[]
for fp in files:
    text=fp.read_text(encoding='utf-8', errors='replace')
    for m in re.finditer(r"<!-- interest-entry: (.*?) -->(.*?)<!-- /interest-entry: \1 -->", text, re.S):
        url=m.group(1).strip(); body=m.group(2)
        t=re.search(r"^##\s+(.+)$", body, re.M)
        title=t.group(1).strip() if t else '(无标题)'
        cat=re.search(r"- 列表命中关键词:\s*(.+)", body)
        kws=re.search(r"- 新增候选关键词:\s*(.+)", body)
        focus_sec=re.search(r"### 本篇关注重点\n(.*?)(?:\n###|\Z)", body, re.S)
        focus=(focus_sec.group(1).strip() if focus_sec else '')
        entries.append({'file':fp.name,'url':url,'title':title,'matched':cat.group(1).strip() if cat else '', 'keywords':kws.group(1).strip() if kws else '', 'focus':focus})
print('ENTRY_COUNT',len(entries))
# top matched categories/tags
counter=collections.Counter()
for e in entries:
    for token in re.split(r"[、,，/]", e['matched']):
        token=token.strip()
        if token and token not in ['(无)','待补充']:
            counter[token]+=1
print('TOP_MATCHED')
for k,v in counter.most_common(20):
    print(k,v)
print('SAMPLES')
for e in entries[:30]:
    print(e['file'],'|',e['title'],'|',e['url'])
