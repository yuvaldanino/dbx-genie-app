# UI Updates — Testing & Integration Tracker

Changes validated in the component sandbox (`test.html`). Apply to real app once all testing is complete.

## Validated Changes (Ready to Apply)

### 1. Markdown Rendering in Chat Responses
**Problem:** Genie responses with markdown (`**bold**`, `- lists`) rendered as plain text in a cramped `<p>` tag.
**Fix:**
- Replace `<p className="text-sm">{r.description}</p>` with `<Markdown components={mdComponents}>{r.description}</Markdown>`
- Wrap in `<Card className="p-5 bg-accent/5 border-accent/20">` for visual prominence
- Remove tiny "Response" label — the description is self-evident
- Add heading support (h1-h3) to markdown component overrides
- Better spacing: `leading-relaxed`, `mb-2`, `space-y-1` on list items

**Files to modify:**
- `src/genieapp/ui/components/apx/templates/QueryWorkspace.tsx` — use Markdown + Card for description
- `src/genieapp/ui/components/apx/MessageBubble.tsx` — import shared mdComponents
- **New:** `src/genieapp/ui/components/apx/md-components.tsx` — shared markdown overrides

**Tested in:** Sandbox scenarios 0-6 (deposit balance, revenue, forkable, error, KPI, long description, loading)

---

### 2. Chart & Visualization Polish
**Problem:** Charts don't match Databricks Genie quality — raw column names on axes/tooltips, no number abbreviation, hard-to-read tooltips, x-axis labels cut off for long names.
**Fix:**
- `formatColumnName()` — converts `total_balance` → "Total Balance" for axis selectors, legend, tooltips
- `formatAxisTick()` — abbreviated Y-axis numbers: `45000` → `45K`, `2000000` → `2M`
- Custom tooltip component — clean card with category name prominent, color dot, formatted column name + value
- Angled X-axis labels (35deg) when values are longer than 10 chars (e.g. restaurant names)
- Visible tick labels in dark mode (`fill: hsl(var(--foreground))`, `opacity: 0.7`)
- Pie chart → donut style (`innerRadius={40}`) with `paddingAngle={2}` for cleaner look
- Legend shows formatted column names
- Cursor highlight on bar hover (`opacity: 0.3`)

**Files to modify:**
- `src/genieapp/ui/components/apx/ChartRenderer.tsx` — apply all formatting improvements

**Tested in:** Sandbox scenarios 0, 1, 2, 5 (bar charts, pie chart, long labels, tooltip)

---

### 3. Homepage Layout — Wider, More Spacious Form
**Problem:** Create space form is a narrow vertical rectangle (`max-w-lg` = 512px), feels cramped — hard to see description, inputs are tiny.
**Fix:**
- Wider card: `max-w-lg` → `max-w-4xl` (container `max-w-4xl` instead of `max-w-2xl`)
- 2-column grid for Company Name + Logo (side by side on md+)
- Taller textareas: description `min-h-[150px]`, questions `min-h-[110px]`
- More padding: `p-8` (was `p-6`), gaps `space-y-6` (was `space-y-5`)
- Taller inputs: `h-11` (was default), taller button: `h-12 text-base`
- Textarea padding: `px-4 py-3` (was `px-3 py-2`)

**Files to modify:**
- `src/genieapp/ui/routes/index.tsx` — widen card, 2-col grid, bigger textareas

**Tested in:** Sandbox scenario 7 (Homepage)

---

### 4. Dark Mode Contrast Improvements
**Problem:** Background (`oklch 0.16`) and card (`oklch 0.19`) are only 3% apart in lightness — everything blends together, "black on black."
**Fix:** Adjust dark mode CSS variables in `globals.css`:
```
--background: oklch(0.13 0.01 260)   (was 0.16, deeper)
--card:       oklch(0.21 0.015 260)  (was 0.19, lighter cards)
--border:     oklch(0.33 0.015 260)  (was 0.28, visible edges)
--input:      oklch(0.33 0.015 260)  (match border)
--muted:      oklch(0.27 0.01 260)   (was 0.25)
--secondary:  oklch(0.27 0.02 260)   (was 0.25)
```
Also add `shadow-sm` to cards in QueryResult for subtle depth.

**Files to modify:**
- `src/genieapp/ui/styles/globals.css` — update `.dark` CSS variables

**Tested in:** All sandbox scenarios (0-7) — cards, charts, homepage all have clear visual separation

---

## Backlog

_(Add future UI fixes here as we identify them)_
