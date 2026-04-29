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

### 5. Remove "Connect Existing" Button + Add "Logged in as" Indicator
**Problem:** "Connect Existing" (BYOG) button on spaces page is not needed for the demo. No user identity shown anywhere.
**Fix:**
- Spaces page: Remove "Connect Existing" button and all BYOG form code/state
- Spaces page: Add "Logged in as [email]" at top using `useAuth().user?.email`
- Homepage: Add "Logged in as [email]" at top left (next to Help button at top right)

**Files to modify:**
- `src/genieapp/ui/routes/spaces.tsx` — remove BYOG button/form, add logged-in indicator
- `src/genieapp/ui/routes/index.tsx` — add logged-in indicator at top

**Tested in:** Sandbox scenarios 7 (Homepage) and 8 (Spaces Page)

---

### 6. Homepage: Replace "View Previous Sessions" with "View All Genie Spaces"
**Problem:** "View Previous Sessions" ghost link at the bottom was hidden, confusing, and poorly labeled.
**Fix:**
- Remove the ghost link at the bottom of the page
- Add a prominent outlined button between the subtitle and form card: "View All Genie Spaces" with sparkle icon + arrow
- Styled with primary-tinted border for visibility without competing with the main CTA

**Files to modify:**
- `src/genieapp/ui/routes/index.tsx` — replace bottom ghost link with prominent button above form

**Tested in:** Sandbox scenario 7 (Homepage)

---

### 7. Sidebar "Home" Button → Navigate to Spaces Page (not Create Page)
**Problem:** The Home button in the sidebar layout (`_sidebar/route.tsx`) navigates to `/` (the create form). Users expect Home to take them back to their spaces list, not the creation page — especially since "Create New" buttons already exist on the spaces page.
**Fix:** Change the Home button's `navigate({ to: "/" })` to `navigate({ to: "/spaces" })`.
**File to modify:** `src/genieapp/ui/routes/_sidebar/route.tsx` — update Home button onClick

**No sandbox test needed — single route change.**

---

### 8. Brand Color System Overhaul — Dark Mode Contrast + Chart Visibility
**Problem:** When a space loads, `BrandThemeInjector` overrides ALL CSS variables (including our contrast fixes from #4) with brand-tinted values from `color-utils.ts`. Current issues:
- Background 0.18, Card 0.22 → only 4% gap (same "black on black")
- Border at 0.30 → too faint
- Neutral chroma at 0.035 → aggressive tinting (Nike orange = brownish everything)
- Chart colors get +0.07 lightness bump → not enough for dark charts
- No minimum contrast enforcement — Nike's #111111 primary is invisible

**Fix — `color-utils.ts` `deriveTheme()` dark mode block:**

Neutrals (match globals.css, reduce chroma):
```
background: tinted(hue, 0.13, 0.015)   // was 0.18, 0.035
card:       tinted(hue, 0.21, 0.015)   // was 0.22, 0.04
border:     tinted(hue, 0.33, 0.015)   // was 0.30, 0.025
muted:      tinted(hue, 0.27, 0.015)   // was 0.26, 0.03
```

Primary/accent:
```
darkBump: 0.10 (was 0.07)
clamp minimum lightness to 0.55 (so Nike #111111 → visible orange-ish)
```

Chart colors — lightness spread (keeps brand hues, no hue rotation):
```
1. Bump all by +0.10, clamp floor to 0.45
2. Check if all 5 are within 0.15 lightness range (clustered)
3. If clustered → redistribute to targets [0.65, 0.55, 0.75, 0.60, 0.70]
   while keeping each color's original hue and chroma
4. Also ensure minimum chroma of 0.08 so colors aren't washed out
```

**Reference implementation:** `src/genieapp/ui/test-color-themes.tsx` → `deriveThemeImproved()` and `spreadLightness()` functions

**Fix — `theme_generator.py` LLM prompt (enhancement):**
- Add: "This app uses dark mode (bg ~#1a1a1a). Colors must be vibrant enough to be visible on dark backgrounds"
- Add: "Chart colors appear side-by-side on the same chart — ensure they are distinguishable by either hue or lightness"
- Add: "If the brand's signature color is very dark (like black), use their most recognizable vibrant color instead"

**Files to modify:**
- `src/genieapp/ui/lib/color-utils.ts` — update `deriveTheme()` dark mode block
- `src/genieapp/backend/pipeline/theme_generator.py` — improve LLM prompt
- `scripts/pipeline/01_design_and_generate.ipynb` — same prompt update in notebook

**Tested in:** Sandbox scenario 9 (Color Themes Side-by-Side) — verified with Nike, Coca-Cola, Spotify, Starbucks, Forkable. All brands keep their identity while being visible and distinguishable on dark backgrounds.

---

## Backlog

_(Add future UI fixes here as we identify them)_
