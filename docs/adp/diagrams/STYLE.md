# Track 4 animated diagram style (shared by every diagram)

Output: hand-written, self-contained SVG files in `docs/adp/diagrams/`, embedded in
GitHub Markdown with `<img src="...">`. No JavaScript, no external fonts, images or
links (GitHub serves SVG through an image proxy: scripts never run, CSS and SMIL do).

## Canvas
- Root: `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="H" viewBox="0 0 960 H" role="img" aria-labelledby="t d">`
  with `<title id="t">` and `<desc id="d">` (one sentence each). H is a multiple of 8.
- First child after style/defs: a background card
  `<rect class="bg" x="0.5" y="0.5" width="959" height="H-1" rx="16"/>`.
- 8 px grid. Outer padding 32. Title baseline y=44 (x=32), subtitle baseline y=68.
  Content starts at y>=96. Keep >=24 px between unrelated boxes, >=16 px text padding inside boxes.
- Align columns and rows exactly: reuse the same x for boxes in a column and the same y
  for boxes in a row. Connectors are orthogonal (horizontal/vertical segments, rounded
  corners via path `Q` or small arcs) or straight; never diagonal spaghetti.

## Type
- `font-family: ui-sans-serif, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif`
  on the root; monospace (`ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`)
  for identifiers (table names, reason codes, functions).
- Title 20px/700, subtitle 13px/400 muted, node label 14px/600, node detail 12px/400,
  small caption/legend 11px. Never below 11px. Use `text-anchor="middle"` for centred
  labels and compute box widths so the longest line fits with 16 px each side
  (estimate 7.6 px per char at 14px/600, 6.6 px at 12px, 7.2 px at 12px mono).

## Colour (CSS variables in one `<style>`, light default + dark override)
```
:root{ --bg:#ffffff; --ink:#0f172a; --muted:#64748b; --line:#94a3b8; --grid:#e2e8f0;
  --blue:#2563eb;  --blue-f:#eff6ff;   /* data / ingestion */
  --teal:#0e7490;  --teal-f:#ecfeff;   /* Azure / platform / CI */
  --violet:#7c3aed;--violet-f:#f5f3ff; /* model / agent */
  --green:#15803d; --green-f:#f0fdf4;  /* pass / routed / success */
  --amber:#b45309; --amber-f:#fffbeb;  /* quarantine / warning / human */
  --red:#b91c1c;   --red-f:#fef2f2;    /* fail / refused */
  --slate:#475569; --slate-f:#f8fafc; }/* neutral / storage */
@media (prefers-color-scheme: dark){ :root{ --bg:#0d1117; --ink:#e6edf3; --muted:#8b949e;
  --line:#6e7681; --grid:#21262d;
  --blue:#58a6ff; --blue-f:#0d1d33; --teal:#39c5cf; --teal-f:#0b2226;
  --violet:#bc8cff; --violet-f:#1d1530; --green:#3fb950; --green-f:#0f2417;
  --amber:#d29922; --amber-f:#2a1f08; --red:#f85149; --red-f:#2d1214;
  --slate:#8b949e; --slate-f:#161b22; } }
```
- `.bg{fill:var(--bg);stroke:var(--grid)}`. Text uses `fill:var(--ink)` / `var(--muted)`.
- Node = rounded rect rx=10, fill `var(--X-f)`, stroke `var(--X)` 1.5px; its label in ink,
  an optional small tag/eyebrow (11px, 600, uppercase, letter-spacing .06em) in `var(--X)`.
- Connectors: stroke `var(--line)` 1.5px, `fill:none`, arrowheads via one `<marker>` whose
  path uses `fill:var(--line)` (define per colour if you need coloured arrows).
- Colour carries meaning only together with a text label (accessibility).

## Animation (subtle, purposeful, loops)
- Flow on connectors: add class `flow` = `stroke-dasharray:6 6; animation:dash 1.2s linear infinite`
  with `@keyframes dash{to{stroke-dashoffset:-12}}`.
- Moving "packets": small circles r=4–5 with `<animateMotion dur="..s" repeatCount="indefinite" begin="..s" path="..."/>`
  (or `<mpath>`), coloured by meaning; stagger with `begin`. Use `keyPoints/keyTimes` or
  opacity `<animate>` to fade them in/out at ends.
- Highlight pulses: `@keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}` or a soft
  stroke-width/opacity glow on the active node, staggered along the path so the eye follows
  the sequence. One full story loop 6–12 s.
- The **static first frame must be complete and readable**: every box, label and connector
  is visible at t=0; animation only adds motion/highlight (no element starts hidden except
  transient packets). Add
  `@media (prefers-reduced-motion: reduce){*{animation:none!important}}`.
- No flashing faster than 3 Hz; no layout motion of text.

## Quality bar / checks
- Validate XML: `python3 -c "import xml.dom.minidom,sys;xml.dom.minidom.parse(sys.argv[1])" f.svg`
- Render both themes: `scripts/render_svg.sh docs/adp/diagrams/NN-name.svg [seconds]`, then
  READ both PNGs and fix: overlapping/clipped text, text outside boxes, misaligned rows or
  columns, arrows that miss boxes, unequal gaps, poor dark-mode contrast. Iterate until clean.
- Facts in diagrams must match the brief exactly (names, numbers, reason codes). Don't invent.
- Keep each file < 40 KB, tidy and indented, with short comments separating sections.
