"""Resolve catalog songs to embeddable YouTube videos and derive hook points
from YouTube's 'most replayed' heatmap."""
import json, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

def get(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(4 * (i + 1)); continue
            return e.code, ""
        except Exception:
            time.sleep(1 + i)
    return 0, ""

def dur(s):
    p = [int(x) for x in s.split(":")]
    t = 0
    for x in p: t = t * 60 + x
    return t

def initial_data(html):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    return json.loads(m.group(1)) if m else None

def walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: yield v
            else: yield from walk(v, key)
    elif isinstance(o, list):
        for v in o: yield from walk(v, key)

BAD = re.compile(r"(lyric|lyrical|slowed|reverb|8d|cover|karaoke|instrumental|remix|mashup|jukebox|full album|1 hour|loop|nonstop|non-stop|reaction|dance cover|tutorial|lofi|lo-fi|status|ringtone)", re.I)

OFFICIAL = re.compile(r"(t-series|sony music|zee music|saregama|tips|speed records|yrf|eros|white hill|desi melodies|geet mp3|brown boys|vevo|lahari|aditya music|think music|sun tv|sony music south|junglee|venus|shemaroo|universal music|warner|atlantic|columbia|republic|interscope|polydor|spinz|t-series apna punjab|jjust music|everest|video palace|times music|ultra|official|topic|vyrl|panorama|rajshri|unisys|wave music|worldwide records|sagahits|5911|amuse|hommie|batra|humble|vip records|ishtar|believe|navraj|rehaan|kv music|zee studios)", re.I)

def search(title, artist):
    q = f"{title} {artist.split(',')[0]} official video"
    st, html = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
    d = initial_data(html) if html else None
    if not d: return []
    out = []
    for vr in walk(d, "videoRenderer"):
        vid = vr.get("videoId")
        t = "".join(r.get("text", "") for r in vr.get("title", {}).get("runs", []))
        ch = "".join(r.get("text", "") for r in vr.get("ownerText", {}).get("runs", []))
        lt = vr.get("lengthText", {}).get("simpleText")
        if not vid or not lt: continue
        out.append({"id": vid, "t": t, "ch": ch, "len": dur(lt)})
    return out

def pick(cands, title):
    tw = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) > 1] or [title.lower()]
    best = None
    for i, c in enumerate(cands[:8]):
        if not (90 <= c["len"] <= 480): continue
        if BAD.search(c["t"]): continue
        lt = c["t"].lower()
        hit = sum(1 for w in tw if w in lt) / len(tw)
        if hit < 0.5: continue
        score = hit * 3 - i * 0.4 + (1 if re.search(r"official|video song|full video|music video", lt) else 0)
        if OFFICIAL.search(c["ch"]): score += 2
        if best is None or score > best[0]: best = (score, c)
    return best[1] if best else None

def embeddable(vid):
    st, _ = get(f"https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v={vid}")
    return st == 200

def heatmap(vid):
    for _ in range(3):
        st, html = get(f"https://www.youtube.com/watch?v={vid}")
        if "MARKER_TYPE_HEATMAP" in html or "heatMarkers" in html or st == 200 and "playabilityStatus" in html and len(html) > 500000: break
        time.sleep(3)
    m = re.search(r'"markerType":"MARKER_TYPE_HEATMAP","markers":(\[.*?\])', html)
    if not m:
        m = re.search(r'"heatMarkers":(\[.*?\])\s*,\s*"heatMarkersDecorations"', html)
        if not m: return None
        raw = json.loads(m.group(1))
        return [(int(x["heatMarkerRenderer"]["timeRangeStartMillis"]) / 1000,
                 int(x["heatMarkerRenderer"]["markerDurationMillis"]) / 1000,
                 float(x["heatMarkerRenderer"]["heatMarkerIntensityScoreNormalized"])) for x in raw]
    raw = json.loads(m.group(1))
    return [(int(x["startMillis"]) / 1000, int(x["durationMillis"]) / 1000,
             float(x["intensityScoreNormalized"])) for x in raw]

def hook_from(hm, length):
    """Hook = start of the most-replayed region after the intro."""
    n = len(hm)
    lo = max(1, int(n * 0.08)); hi = int(n * 0.85)
    seg = hm[lo:hi]
    # smooth over 3 markers so single spikes don't win
    sm = [sum(seg[max(0, i - 1):i + 2][j][2] for j in range(len(seg[max(0, i - 1):i + 2]))) / len(seg[max(0, i - 1):i + 2]) for i in range(len(seg))]
    pi = max(range(len(sm)), key=lambda i: sm[i])
    peak = sm[pi]
    i = pi
    while i > 0 and sm[i - 1] >= peak * 0.72: i -= 1
    j = pi
    while j < len(sm) - 1 and sm[j + 1] >= peak * 0.45: j += 1
    start = max(0, seg[i][0] - 2)
    end = seg[j][0] + seg[j][1]
    play = max(55, min(105, end - start + 15))
    return round(start, 1), round(play), round(peak, 2)

def resolve(row):
    title, artist = row["title"], row["artist"]
    c = pick(search(title, artist), title)
    if not c: return {**row, "err": "no match"}
    if not embeddable(c["id"]):
        # try the next best candidate once
        return {**row, "err": "not embeddable", "yt": c["id"]}
    hm = heatmap(c["id"])
    if hm and len(hm) > 20:
        h, play, conf = hook_from(hm, c["len"])
        src = "replay"
    else:
        h, play, conf, src = round(c["len"] * 0.28), 75, 0, "estimate"
    return {**row, "yt": c["id"], "ytTitle": c["t"], "channel": c["ch"], "len": c["len"],
            "hook": h, "play": play, "hookSrc": src, "conf": conf}

def main():
    rows = []
    for line in open(sys.argv[1], encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        t, a, l, y, e, b, tags = line.split("|")
        rows.append({"title": t, "artist": a, "lang": l, "year": int(y), "energy": int(e),
                     "bpm": int(b), "tags": tags.split(",")})
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(resolve, rows))
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ok = [r for r in res if "yt" in r and "err" not in r]
    print(f"{len(ok)}/{len(res)} resolved; replay hooks: {sum(r.get('hookSrc')=='replay' for r in ok)}")
    for r in res:
        if "err" in r: print("  FAIL", r["title"], "-", r["err"])

if __name__ == "__main__":
    main()
