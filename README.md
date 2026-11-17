# HOOKD: an auto-DJ prototype

A single-page party DJ. Pick the occasion, languages, crowd and vibe, and it plans the whole night as an energy curve. Every song starts at its replay peak (the hook) and crossfades into the next.

## Run it
YouTube won't play from a file opened by double-click, or inside a Claude artifact. Serve the page from a web address:

- **Fastest:** drag the `index.html` file onto https://app.netlify.com/drop. You get a live link in about 10 seconds.
- **Vercel:** `npx vercel` in this folder.
- **Local:** run `python3 -m http.server 8000` in this folder, then open http://localhost:8000.

Keyboard: Space pauses, → skips, ↑/↓ retune the energy.

## What's better than NAUX
| | NAUX | HOOKD |
|---|---|---|
| Hook point | Hand-picked | YouTube "most replayed" peak, plus tap-to-fix that's saved |
| Set logic | Mood + time of night | Energy curve over the whole night (warm-up → peak → breather → peak → wind-down), BPM-smooth transitions, artist spacing, language switching |
| Explains picks | No | Each queued song shows why it's there (tempo, energy ↑, language switch, wedding staple…) |
| Learns | Hook dragging | Fast skip = less like it; ♥ / play full = more; removed songs and artists are down-ranked. Kept per device |
| Live control | Skip, play full | Plus "More energy" / "Bring it down" (retunes the next 15 min), reshuffle, requests pinned to play next |
| Regional | No Marathi | Marathi, Ganpati, Navratri, South kuthu/mass, Haryanvi/Bhojpuri |

## Library pipeline
- `catalog.txt`: one song per line, `title|artist|lang|year|energy|bpm|tags`. **The energy and BPM values are hand estimates.** Fix them as you test.
- `resolve.py catalog.txt resolved.json`: finds the official YouTube video, checks that it can be embedded, and reads the most-replayed curve to set the hook.
- `hooks.py`: refetches the replay curves and recomputes the hooks.
- After adding songs, rebuild `index.html` by injecting `resolved.json` into `app.template.html` (replace `/*__DATA__*/`).

## Known limits (prototype)
- On iPhone, the iOS browser ignores volume control, so crossfades become quick cuts.
- YouTube ads can play without YouTube Premium. Some videos get region-blocked; those are skipped automatically and down-ranked.
- For private parties only. Venues need IPRS/PPL public-performance licences.
