import json, pathlib
root=pathlib.Path(r"C:\Users\Qiang\.openclaw\workspace-lexmechanic\memory\eeworld-source-code")
urls=[
"https://www.eeworld.com.cn/IoT/eic719582.html",
"https://www.eeworld.com.cn/IoT/eic719581.html",
"https://www.eeworld.com.cn/mcu/eic719130.html",
]
for u in urls:
    found=False
    for p in sorted(root.glob('*.json'), key=lambda x:x.stat().st_mtime, reverse=True):
        try:
            d=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        for it in d.get('ranked',[]):
            if isinstance(it,dict) and it.get('url')==u:
                print('FOUND',u)
                print(' file=',p.name)
                print(' date=',it.get('date'))
                print(' category=',it.get('category'))
                print(' title=',it.get('title'))
                found=True
                break
        if found:
            break
    if not found:
        print('MISS',u)
