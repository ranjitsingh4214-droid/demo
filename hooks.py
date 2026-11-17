import json, re, time, resolve as R
from concurrent.futures import ThreadPoolExecutor
data = json.load(open('resolved.json'))

def curve(vid):
    hm = R.heatmap(vid)
    if not hm or len(hm) < 20: return None, None
    length = hm[-1][0] + hm[-1][1]
    return [h[2] for h in hm], length

def hook(v, length):
    n = len(v); step = length / n
    sm = [sum(v[max(0,i-1):i+2]) / len(v[max(0,i-1):i+2]) for i in range(n)]
    i = int(n * 0.05)
    while i < int(n * 0.3) and sm[i+1] <= sm[i] + 0.01: i += 1   # ride down the intro spike
    lo = max(i, int(n * 0.08)); hi = int(n * 0.88)
    pk = max(range(lo, hi), key=lambda k: sm[k]); peak = sm[pk]
    a = pk
    while a > lo and sm[a-1] >= peak * 0.75: a -= 1
    b = pk
    while b < n - 1 and sm[b+1] >= peak * 0.5: b += 1
    start = max(0, a * step - 1.5)
    play = max(45, min(100, (b + 1) * step - start + 10))
    return round(start, 1), round(play), round(peak, 2)

def work(r):
    v, length = curve(r["yt"])
    if v:
        h, p, c = hook(v, length)
        r.update(hook=h, play=p, conf=c, hookSrc="replay", len=round(length),
                 hm=[round(x * 99) for x in v[::2]])
    else:
        r.update(hookSrc="estimate", hm=None)
        if r.get("channel") == "override": r.update(hook=45, play=75, len=r.get("len", 220))
    return r

with ThreadPoolExecutor(3) as ex: data = list(ex.map(work, data))
json.dump(data, open('resolved.json','w'), ensure_ascii=False, indent=0)
print(sum(r["hookSrc"]=="replay" for r in data), "/", len(data))
for r in data[:12]+data[-8:]: print(r["title"][:24].ljust(24), r["hook"], r["play"], r.get("len"), r["hookSrc"])
