import re, subprocess, datetime
from urllib.request import Request, urlopen

urls = [
    "https://www.eeworld.com.cn/emp/zhonglintanxin/a423077.jspx",
    "https://www.eeworld.com.cn/emp/DigiKey/a422730.jspx",
    "https://www.eeworld.com.cn/emp/DigiKey/a422728.jspx",
]
script = r"C:\Users\Qiang\.openclaw\workspace-lexmechanic\skills\eeworld-reader\scripts\eeworld_feed.py"

def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()

def norm_date(s):
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if not m:
        return datetime.date.today().isoformat()
    y, mo, d = map(int, m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"

def fetch_meta(url):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(req, timeout=20) as r:
        raw = r.read()
    text = None
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            pass
    if text is None:
        text = raw.decode("utf-8", errors="replace")

    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I|re.S)
    title = strip_tags(h1.group(1)) if h1 else ""
    if not title:
        t = re.search(r"<title[^>]*>(.*?)</title>", text, re.I|re.S)
        title = strip_tags(t.group(1)) if t else url
        title = title.split("-")[0].strip()

    date = ""
    for pat in [
        r"(?:发布时间|更新|日期|時間)[^0-9]{0,12}(20\d{2}-\d{1,2}-\d{1,2})",
        r"(20\d{2}-\d{1,2}-\d{1,2})",
    ]:
        m = re.search(pat, text)
        if m:
            date = norm_date(m.group(1))
            break
    if not date:
        date = datetime.date.today().isoformat()
    return title, date

for url in urls:
    title, date = fetch_meta(url)
    summary = "用户指定本篇为感兴趣，已按文章时间入档。待后续逐篇阅读后补充技术摘要、问答要点与关注重点。"
    focus = "- 本条为用户显式标记感兴趣\n- 当前先完成按文章时间归档\n- 后续逐篇阅读后补全技术结论"
    cmd = [
        "python", script, "interest-save",
        "--title", title,
        "--url", url,
        "--summary", summary,
        "--keywords", "待精读,感兴趣",
        "--matched-keywords", "待补充",
        "--score", "0.00",
        "--date", date,
        "--category", "嵌入式系统",
        "--focus", focus,
        "--no-sync-profile",
        "--format", "json",
    ]
    subprocess.run(cmd, check=False)
    print(f"RECORDED\t{date}\t{title}\t{url}")
