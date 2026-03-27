# OpenClaw Web Fetch Fallback

When OpenClaw can open a URL but fails to extract meaningful page content, use Agent Reach's generic web channel as the fallback reader.

This method worked for:

- `https://www.eeworld.com.cn/latestnews`

The effective readable source for that page was:

- `http://www.eeworld.com.cn/latestnews`
- Jina Reader URL: `https://r.jina.ai/http://www.eeworld.com.cn/latestnews`

## Why this fallback works

Some pages render badly for normal crawlers because of one or more of these issues:

- aggressive anti-bot behavior
- HTML structure that is noisy but not semantically useful
- client-side rendering or partial rendering
- redirects between `https` and `http`
- Windows `curl.exe` TLS or `schannel` issues
- Windows console encoding problems when printing scraped text

Agent Reach's "any web page" channel delegates the page to Jina Reader, which returns a cleaned Markdown version of the page. For content summarization or section extraction, this is often more useful than raw HTML.

## Recommended fallback order

1. Try OpenClaw's normal page fetch.
2. If the page body is empty or unusable, run `agent-reach doctor`.
3. If `doctor` shows the generic web channel is available, retry through Jina Reader.
4. If `curl.exe` fails on Windows, use Python from the Agent Reach virtual environment instead of `curl.exe`.
5. Only fall back to a browser automation scraper if Jina Reader also fails.

## Step 1: verify the channel

```powershell
agent-reach doctor
```

You want to see a healthy status for the generic web channel, similar to:

- arbitrary web pages are readable through Jina Reader

## Step 2: try the direct Jina Reader URL

```powershell
curl.exe -L "https://r.jina.ai/http://www.eeworld.com.cn/latestnews"
```

Notes:

- The Jina URL is `https://r.jina.ai/` followed by the original URL.
- Keep the original scheme in the suffix.
- If the shared link is `https://...` but the site actually serves cleaner content on `http://...`, use the canonical URL that works in practice.

## Step 3: if Windows curl fails, use Python

On this machine, `curl.exe` hit TLS handshake failures against `r.jina.ai`. Python `requests` from the Agent Reach venv was more reliable.

```powershell
$env:PYTHONIOENCODING='utf-8'
C:\Users\Qiang\.agent-reach-venv\Scripts\python.exe -c "import requests; u='https://r.jina.ai/http://www.eeworld.com.cn/latestnews'; r=requests.get(u, timeout=60); print(r.status_code); print(r.text[:12000])"
```

Why the extra environment variable:

- Jina output may contain zero-width or other Unicode characters.
- Without UTF-8 output, Windows consoles using GBK may throw `UnicodeEncodeError`.

## Step 4: add retry logic

The Jina backend can be intermittently reset by the remote side. A short retry loop makes the fetch much more stable.

```powershell
$env:PYTHONIOENCODING='utf-8'
C:\Users\Qiang\.agent-reach-venv\Scripts\python.exe -c "import requests,time,sys; u='https://r.jina.ai/http://www.eeworld.com.cn/latestnews'; last=None
for i in range(5):
    try:
        r=requests.get(u, timeout=60)
        print('STATUS', r.status_code)
        text=r.text.encode('utf-8','replace').decode('utf-8','replace')
        print(text[:25000])
        sys.exit(0)
    except Exception as e:
        last=e
        print('RETRY', i+1, repr(e), file=sys.stderr)
        time.sleep(2)
raise SystemExit(last)"
```



## When not to use this fallback

Do not rely on Jina Reader for:

- WeChat article bodies that require the dedicated WeChat reader
- login-gated pages
- highly interactive apps where data is loaded after authentication
- sites where you need exact DOM selectors rather than readable content

## Suggested OpenClaw integration

If you want this behavior in OpenClaw itself, add a generic-web fallback with this decision rule:

1. native fetch succeeds and body length is reasonable: use native content
2. native fetch returns empty or mostly boilerplate: call Jina Reader
3. Jina Reader succeeds: parse Markdown
4. Jina Reader fails: escalate to browser automation or channel-specific scraper

Minimal output contract:

```json
{
  "title": "page title",
  "source_url": "canonical page url",
  "content_format": "markdown",
  "content": "cleaned markdown body"
}
```

## Known failure signatures

If you see these symptoms, switch to the Python retry path immediately:

- `curl: (35) schannel: failed to receive handshake`
- `UnicodeEncodeError: 'gbk' codec can't encode character`
- `ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接')`

These are transport or console issues, not proof that the page itself is unreadable.
