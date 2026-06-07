# KPA Graphical Review / Editing — Strategy Options

**Author:** Scotty
**Date:** 2026-06-07
**Status:** RESEARCH NOTE — for Captain decision on phase-3+ UI strategy

> Per Captain's 2026-06-07 07:30 PDT directive: "There's a reasonable
> open question as how best to enable a graphical review and editing
> capability. ... Research possibilities and propose a few options."

---

## What's actually new in the world (2026-04-17)

Anthropic launched **Claude Design** by Anthropic Labs:

- Powered by **Claude Opus 4.7** (vision-capable).
- Two-pane UX: chat on the left, **live HTML canvas on the right**.
- Native exports: **PPTX, PDF, HTML, Canva**.
- Native imports: text prompts, **DOCX, PPTX, XLSX**, codebase, URL capture.
- "Brand built in" — reads codebase + design files to extract a design
  system; reuses colors / typography / components automatically across
  projects.
- Handoff bundle to Claude Code (single instruction → production code).
- Available now in research preview for Pro / Max / Team / Enterprise.
- **MCP integration: not yet open. Anthropic said "over the coming weeks,
  we'll make it easier to build integrations with Claude Design"** —
  they shipped Apr 17, so the integration surface is becoming public
  imminently (weeks → months).

**Crucial observation: Claude Design exports PPTX, NOT `.key`.** That's
precisely the gap KPA fills. Anyone wanting a native editable Keynote
file out of Claude Design today has to:
1. Export PPTX → 2. Open in Keynote.app → 3. Re-save as `.key`.

Step 2 is lossy (PPTX → Keynote conversion silently re-flows text,
re-maps fonts, drops Keynote-specific features). KPA + Claude Design
collapses that to a single native pipeline.

## Captain's two starting options (restated)

- **Option A** — MCP bridge: Claude Design ↔ `.key` via KPA. Pixel-
  perfect import/export. Claude Design is the GUI; KPA is the codec.
- **Option B** — Build our own HTML-canvas review/edit surface (Claude
  Design–like) into KPA itself.

## Five concrete options (broader than A/B above)

### Option 1 — Claude Design MCP integration (Captain's A)

**Architecture:** KPA exposes its existing MCP server (Step 7) with two
extra tools:

- `kpa_export_to_canvas(deck_path) → html bundle + asset manifest` — KPA
  reads a `.key`, renders to the HTML representation Claude Design's
  canvas can ingest.
- `kpa_import_from_canvas(html bundle) → deck_path` — Claude Design hands
  KPA back its HTML bundle; KPA emits a `.key`.

**Pros:**
- We piggyback on Anthropic's UX, vision model, and brand-system
  intelligence. They iterate; we benefit.
- Aligns with Captain's North Star ("any LLM tool runner in our legion").
- Smallest scope addition to KPA — just two MCP tools and the HTML ↔ IWA
  mapper.
- Brand asset library (Q4 from the brief) becomes a Claude Design
  design system entry automatically.
- Works the day Anthropic opens the MCP surface.

**Cons:**
- Requires Anthropic to open Claude Design to third-party MCP servers.
  Announced as "coming weeks" Apr 17 — that's a soft ETA, not a contract.
- The HTML ↔ Keynote mapping is the hard part. Claude Design's HTML is
  freeform component output (React-ish); Keynote's object graph is
  rigid (master/layout/style cascades). The mapper has to be smart, not
  just transcoding.
- We don't control the rendering pipeline — if Claude Design renders a
  shadow we can't emit in Keynote, the export loses fidelity.
- Captain pays Pro/Max/Team/Enterprise — Anthropic gets the UX revenue.
- Anthropic could deprecate / restrict the surface.

**Effort:** ~2-3 weeks once Anthropic ships the MCP integration surface.
**Pixel fidelity:** **Probabilistic.** "Close" not "perfect." Animations
not preserved.

### Option 2 — Keynote.app as the GUI (lightweight, ships now)

**Architecture:** KPA generates a valid `.key`. Captain (or HAL, or the
agent) opens it in Keynote.app. Review and edit happen natively.
Re-saved file is re-ingested by KPA via F1 round-trip.

**Pros:**
- **Pixel-perfect by definition** — Keynote.app *is* the renderer.
- **Animations, transitions, presenter mode, fonts: 100% native.**
- Zero new code; just `kpa.open()` → user edits → `kpa.open()` again.
- Ships today.
- The OS-level "open the deck in the real app" loop is what humans
  already know and trust.
- For HAL/Scotty/Claude agents that don't have a screen, this option
  doesn't help — but it's the human-review story.

**Cons:**
- Requires Keynote.app on the reviewer's machine (Mac-only).
- Not headless — bad for CI / fleet agents / Captain's iPad without
  Keynote.
- Round-trip-with-edit needs F1 to handle Keynote's resave (already
  green for SVEF + NCI).

**Effort:** Zero (already shipping). **Pixel fidelity:** **100%.**
Animations preserved.

### Option 3 — Native HTML preview server (lightweight Claude Design–like)

**Architecture:** Build a thin in-house renderer:

- `kpa preview deck.key` launches a local HTTP server.
- Server renders each slide as an HTML snapshot — KPA reads the IWA
  object graph and emits styled `<div>` / `<svg>` / `<canvas>` blocks
  with positions, fonts, colors.
- Browser shows a thumbnail grid + click-to-edit. Edits POST back to
  KPA which mutates the object graph and re-renders.
- Uses something like FastAPI + a small Lit / vanilla-JS front-end.

**Pros:**
- Headless-friendly (server-side rendering; thumbnails to PNG via
  Playwright). Solves the "agent without a Mac GUI" case.
- No external dependencies (no Claude Design, no Keynote.app).
- We own the entire stack; no rug-pull risk.
- Compatible with Linux runners (CI thumbnails, fleet dashboards).
- Captain can review decks on iPad / phone via the URL.
- Foundation for Option 4 below if we ever want to go bigger.

**Cons:**
- HTML rendering will **never be pixel-identical to Keynote**. Always
  ~85-95% — different font metrics, missing Keynote-specific shadow /
  blur / shaped effects.
- Custom-built UI = ongoing maintenance burden.
- Re-implementing Keynote's animation system in HTML is a rabbit hole
  we should NOT enter. v1: static previews only.
- Significant code: ~2-3 weeks for a usable v1.

**Effort:** 2-3 weeks v1, ongoing maintenance.
**Pixel fidelity:** ~85-95% static; no animations.

### Option 4 — Full Claude-Design-clone inside KPA (Captain's B)

**Architecture:** Option 3 + an LLM-in-the-loop edit pane. Same
two-pane UX as Claude Design but the codec is KPA / `.key` is the
native format, not PPTX.

**Pros:**
- We get all of Claude Design's UX value for `.key`-native workflows.
- We control the surface end-to-end; no Anthropic dependency.
- Captain's legion of agents gets a first-class authoring + review
  experience.

**Cons:**
- **Massive** — this is a 3-6 month effort, not a Phase 1 add-on.
- We're competing with Anthropic Labs on UX, which is a poor use of our
  finite engineering hours.
- Most of the value is duplicative once Anthropic opens the Claude
  Design MCP surface (Option 1).

**Effort:** 3-6 months. **Pixel fidelity:** Same constraints as
Option 3.

### Option 5 — Hybrid: PPTX-bridge using Claude Design TODAY

**Architecture:** Don't wait for Claude Design's MCP surface. Use the
PPTX export today.

- Captain (or agent) uses Claude Design directly in the browser.
- Exports as PPTX (Claude Design ships this natively).
- KPA Phase 2 (already in the PRD §4.3) provides `pptx → key`
  conversion as a first-class import path.
- Result: Claude Design designs the deck; KPA emits the Keynote-native
  output; lossless `.pptx → .key` is the bridge.

**Pros:**
- **Works today** — no Anthropic API gates, no waiting on MCP.
- Leverages Phase 2 of the PRD (already planned).
- Captain gets the Claude Design UX immediately; KPA's job is to make
  the conversion losslessly editable in Keynote.
- Strong native-export quality from Claude Design's PPTX is already
  proven (their canvas → PPTX is high-fidelity per the launch
  testimonials).

**Cons:**
- PPTX is the bottleneck — PowerPoint and Keynote have different
  object models, so even a perfect PPTX → IWA mapper loses some
  Keynote-specific things (mostly fine, since the source is PPTX).
- Animation fidelity: PPTX animations are a different system than
  Keynote builds; some translation needed.
- Doesn't preserve `.key` features that were never in the PPTX source
  (irrelevant if the deck was designed in Claude Design originally).

**Effort:** Phase 2 (already in PRD), no extra work.
**Pixel fidelity:** Inherits Claude Design → PPTX fidelity, then PPTX
→ KEY conversion fidelity. Likely 90-95% with animations partial.

---

## Scotty's recommended sequencing

### Now (Phase 1 — what we're already building)

- Ship F1 ✅, F2 (Step 4 brief), F3-F5 (Steps 5-7).
- Add **Option 2** essentially for free — KPA already produces valid
  `.key` files; Keynote.app opens them. Document the "open in Keynote
  to review" workflow as the official human-review path.

### Phase 1.5 (between F5 and F6)

- Add a small `kpa preview` command — **Option 3 lite**. Render
  static slide thumbnails to PNG via the same code path that powers
  the F2 critic loop (PRD §4.1.G). No interactive editing yet.
- Output: `kpa preview deck.key --out preview/` produces
  `preview/slide-N.png` for every slide. CI uses this for visual
  regression diffs.
- Effort: ~3 days once F2 is green.

### Phase 2 (PPTX + PDF — already in PRD §4.3)

- Implement **Option 5**: PPTX import as a first-class path.
- Claude Design becomes our de facto design GUI for Brainworks-grade
  decks **today**.
- KPA Phase 2 does the lossless PPTX → KEY conversion.
- This is the **fastest path to "design in a real UX, ship as .key"**
  and it doesn't depend on Anthropic opening anything.

### Phase 2.5 (when Anthropic opens Claude Design MCP)

- Implement **Option 1**: register KPA's MCP server with Claude Design.
- Claude Design gains a `.key` export and `.key` import button via our
  server. We become the canonical Keynote integration for Claude Design.
- This is also a great open-source story — first MCP server to extend
  Claude Design with native Keynote support.

### Phase 3+ (optional, only if value justifies it)

- Re-evaluate **Option 4** (full HTML clone). Almost certainly NOT
  worth the engineering hours. We'd be reinventing Claude Design.
- More likely: extend the `kpa preview` server to be interactive (text
  edits, color tweaks, layout nudges) for legion agents that can't
  drive Keynote.app. Mini-Claude-Design for Keynote, not full clone.

---

## Headline recommendation — LOCKED by Captain 2026-06-07 07:42 PDT (reconfirmed 07:43)

**Build order: Option 2 → Option 3-lite → Option 4 → Option 5.**
**Insert Option 1 instantly when Anthropic opens Claude Design MCP.**

**Strict ordering:** Option 4 ships completely before Option 5 starts.
Earlier hedge about "Option 5 might land de facto first via PPTX import"
is retracted per Captain 2026-06-07 07:43 PDT.

Phase mapping:

- **Phase 1 (now)** — ship Option 2 (Keynote.app human review,
  effectively free with F1) and Option 3-lite (`kpa preview` headless
  PNG thumbnails) alongside F2/F3/F4/F5.
- **Phase 2a** — build Option 4 (custom HTML canvas / Claude-Design-like
  surface inside KPA itself). Strategic surface, our IP, brand-controlled,
  no third-party dependency. **Scotty's flag:** 3–6 month lift, but it's
  the differentiator and Captain has prioritized it.
- **Phase 2b** — ship Option 5 (PPTX import / export) as the cross-format
  bridge **after** Option 4 is feature-complete. Commodity interop layer,
  4–6 weeks once Option 4 is solid.
- **Anytime trigger** — monitor Anthropic announcements (cron job runs
  weekly; see DEV_PLAN). The day Claude Design opens its MCP surface to
  third-party servers, KPA's existing MCP server gets two extra tools
  (`kpa_export_to_canvas`, `kpa_import_from_canvas`) and we register as
  the canonical Keynote bridge. Estimated 1–2 weeks of work; queue-jumps
  whatever else is in flight.

### Captain's reinforced clarification (2026-06-07 07:42 PDT)

Surgical editing has two parallel surfaces, both first-class:

1. **Conversational LLM editing** — any aspect of the presentation,
   any granularity, expressed in natural language. "Move the title down
   20%, change the font to Helvetica, swap the hero image on slide 3,
   make the section divider color match our secondary brand teal,
   reduce body copy on slides 4–7 by 30 words each." This routes
   through the same Python API as programmatic edits but via an
   LLM-driven planner that translates intent → API calls.
2. **Physical manipulation via the design tool** — direct
   drag/click/edit in a real UI. Phase 1–2: Keynote.app is the design
   tool. Phase 2 (in parallel with Phase 2 Option 4): KPA's custom
   HTML canvas provides drag/click/edit for fleet agents and
   headless / non-Mac users. Phase 3: if Anthropic Claude Design MCP
   has opened, that becomes the primary external-facing design tool
   via the MCP bridge.

Both surfaces share the same underlying API (Step 4) and brand-
compliance validator. The conversational edit surface is the LLM
planner layer; the physical surface is whichever GUI is in play.

### Scotty's reinforced recommendation (unchanged)

We never bet KPA's value on Anthropic shipping anything. Option 1 is
bonus, not foundation. We always have a working path: Keynote.app for
humans on Macs, KPA's custom canvas for fleet agents, and PPTX bridge
for external partners.

### Reinforced by Captain's 2026-06-07 07:33 PDT clarification

The requirement is **both** end-to-end generation **and** surgical edits
("move title down 20%, change font to Helvetica"). That doesn't change
the option ranking but it sharpens the value:

- **Option 2 (Keynote.app)** becomes the canonical *verification* surface
  for surgical edits. Captain or HAL applies an edit via the API; opens
  the result in Keynote.app to visually confirm; if good, ship.
- **Option 3-lite (`kpa preview`)** becomes the canonical *headless*
  verification surface for fleet agents that don't have Keynote.app —
  they apply an edit, render to PNG, diff against the previous version
  to confirm the edit landed (visual-regression CI).
- **Option 5 (PPTX bridge via Claude Design)** stays the high-level
  *generation* path for partners / external users who want a chat UX
  without writing Python. The surgical-edit power is KPA's API; the
  generation UX is Claude Design.
- **Option 1 (Claude Design MCP)** when it opens will let agents apply
  surgical edits via natural language inside Claude Design itself —
  Claude Design's canvas calls our MCP `kpa_edit_slide` tool.

The API and DSL design in Step 4 should support natural-language-style
edit expressions so that all three surfaces (Python, CLI, MCP) can
express the same edits identically. E.g. all three of:

```
kpa edit deck.key 'slide[3].title.move(dy="20%")'   # CLI sugar
deck.slide[3].title.move(dy="20%")                  # Python API
kpa_edit_slide(path, 3, [{"target": "title",        # MCP / JSON
                          "op": "move",
                          "dy": "20%"}])
```

...should produce **byte-identical output**. That's a Step 4 design
invariant.

**Why:**

- We never bet KPA's value on Anthropic shipping anything (Option 1 is
  bonus, not foundation).
- Captain gets pixel-perfect human review TODAY via Keynote.app.
- Agents get headless preview thumbnails via `kpa preview`.
- "Design the deck in a real GUI, ship as `.key`" is solved via
  Claude Design + Phase-2 PPTX import — no waiting.
- When Claude Design MCP opens, we add a one-week-effort integration
  that makes KPA's MCP server the de facto Keynote bridge.

## Open second-order questions (for Captain when ready)

1. **Brand-asset grovel feature** (from Q4 of Step 4 brief) — should the
   asset library output be Claude-Design-compatible (a "design system"
   doc that Claude Design can ingest)? That would make us doubly useful.
2. **Phase 2 priority** — should PPTX import be moved up from "after
   Phase 1 ships" to "interleaved with Phase 1"? Currently the PRD says
   Phase 1 → Phase 2. Option 5 above argues for parallelizing.
3. **Visual regression threshold** — what's the visual-diff tolerance
   for `kpa preview` thumbnails before we call a change a "regression"?
   PRD §5.1 F3 says 1% for chart fidelity. Same number for slide
   preview? Or looser (5-10%) for HTML-rendered thumbnails?

— Scotty
