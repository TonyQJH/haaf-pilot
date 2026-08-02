# Agent4IR @ KDD 2026 — talk slides

Slidev deck for *Beyond Benchmark Islands: Toward Representative Trustworthiness
Evaluation for Agentic AI*.

Format: **7–8 min presentation + 2–3 min QA**, in-person.

## Structure

| Slides | Content | Budget |
|:--|:--|:--|
| 1 | Title | 0:20 |
| 2–3 | Motivation + the two gaps | 1:35 |
| 4 | Roadmap | 0:25 |
| 5–7 | Definition (P1–P5), HAAF, Layer-4 sampling | 2:15 |
| 8 | Setup + RWF | 0:30 |
| 9–11 | Findings 1–3 | 2:10 |
| 12 | LLM-judge audit of our own labels | 0:35 |
| 13 | Takeaways | 0:20 |
| 14 | Thank you / QA | — |
| 15–26 | Backup slides B1–B11 for QA | — |

## The script

Every main slide's presenter note contains the **full word-for-word script**,
ready to read aloud, followed by delivery cues marked `▸`. Slide 14's note holds
written-out answers to the eight most likely QA questions.

**948 words total.** Measured against reading pace:

| pace | total | verdict |
|:--|:--|:--|
| 115 wpm (slow, careful) | 8:15 | slightly over — use the marked cuts |
| 130 wpm (normal) | **7:17** | target |
| 145 wpm (brisk) | 6:32 | room to breathe on the figures |

Two marked cut points if a rehearsal runs past 8:00: the flagged line on slide 7
(~20s) and the "two families that do improve" sentence on slide 10 (~10s).
Slide 12 (the audit of our own labels) should never be cut — it is the
credibility slide.

Rehearse once with a stopwatch and note your own wpm; the per-slide headers
give you a checkpoint time so you can tell mid-talk whether you are ahead or
behind.

## Commands

```bash
npm install          # once
npm run dev          # live preview at localhost:3030 (press `p` for presenter mode)
npm run build        # static site -> dist-web/
npm run export        # -> dist/…​.pdf     presenter copy
npm run export-pptx   # -> dist/…​.pptx    presenter copy, notes embedded
npm run export-notes  # -> dist/speaker-notes.pdf
npm run export-upload # -> dist/upload/    NOTES STRIPPED — share these
npm run export-all    # all of the above
```

### Two builds: keep them straight

| Folder | Notes inside? | Use |
|:--|:--|:--|
| `dist/` | **yes** (pptx) | your own laptop, presenter view |
| `dist/upload/` | **no** | Google Drive, organisers, anyone else |

`export-upload` runs `scripts/build-upload.mjs`, which strips every `<!-- … -->`
note block from `slides.md` into a temp entry, exports from that, and deletes
the temp. It aborts if it finds no notes to strip or if a cue marker survives,
so a silent failure can't ship a leaky file. Slide content is byte-identical
between the two builds — only the notes differ.

The **PDF never carries notes** in either build (Slidev renders the print view),
so `dist/…​.pdf` is already safe. Only the **PPTX** embeds them — that is the one
that needs the stripped copy.

### About the PPTX

`slidev export --format pptx` renders **each slide as a full-bleed PNG** (at
`--scale 2`, so ~2560×1440 per slide) and wraps them in a 16:9 deck. Consequences:

- Speaker notes **do** carry over — slides 1–14 have them, visible in PowerPoint
  and Keynote presenter view. Backups 15–26 have no notes by design.
- Text is **not editable** in PowerPoint. To change wording, edit `slides.md`
  and re-export. Never hand-edit the pptx — the next export overwrites it.
- File is ~5.5 MB vs 2.4 MB for the PDF.

Prefer the PDF for presenting unless the venue specifically requires .pptx.

Presenter mode (`localhost:3030/presenter`) shows the notes, the next slide, and
a timer — use it on the laptop screen while the projector shows the deck.

The VS Code Slidev extension picks up `slides.md` automatically.

## KDD 2026 visual identity

The palette is **sampled from the official logo artwork**
(`public/KDD26-Logo4-black.png`), not eyeballed from the banner:

| | hex | used for |
|:--|:--|:--|
| ink | `#0A2224` | body text, dark cover/divider background |
| coral | `#F66558` | violations, Control bars, "Gap" tags, accents |
| teal | `#3F8882` | trustworthy values, Treated bars, links, rules |
| light teal | `#61ACA5` | secondary fills |

Text-bearing tokens are darkened from the brand values (`--accent #2E7D71`,
`--warn #CE4436`) so they clear WCAG AA on white; the brand values themselves
stay for fills, chart marks and rules.

- **Dark slides** (cover, thank-you, backup divider) carry `class: kdd-dark`
  and get the ink background plus a soft teal/coral radial wash — an abstraction
  of the banner's woodblock swirl.
- **Logo placement**: full light wordmark on the cover and thank-you slide
  (`kdd-logo-light.png`, generated from the supplied file by repainting the ink
  pixels white), small dark wordmark in the footer of every content slide.
- **Figures** are regenerated in the same palette by
  `python3 scripts/make-figures.py` — coral = violated, teal = trustworthy.
  The diverging ramp keeps a warm cream midpoint rather than white, because a
  near-white mid washes out the 0.4–0.6 band and kills the P3/P4 failure stripe.
  Values are transcribed from the camera-ready tables with a `SOURCE` comment on
  each block, so the figures can be checked against the paper.
  The HAAF schematic is recoloured by remapping its flat pastel fills.

Re-run `scripts/make-figures.py` after any change to the paper's numbers, then
re-export.

## Files

- `slides.md` — the deck; presenter notes are the HTML comments at the end of each slide
- `style.css` — deck styling (cards, tables, colour tokens; light + dark)
- `global-bottom.vue` — footer bar with running slide number
- `public/*.png` — figures rendered at 300 dpi from `Agent4IR_KDD2026/figures/*.pdf`
  and auto-cropped: `coverage`, `framework_haaf`, `profile`, `before_after`

To regenerate a figure after the paper changes:

```bash
pdftoppm -png -r 300 ../Agent4IR_KDD2026/figures/profile_radar.pdf /tmp/profile
# then autocrop whitespace and drop the result into public/
```

## Numbers used in the deck

All taken from the Agent4IR camera-ready (`../Agent4IR_KDD2026/Chapter/`):
13 systems × 7 families × 100 scenarios × 2 configs = 2,600 trajectories;
Layer-4 subset τ = 0.890 / ρ = 0.963; anti-scaling two pairs at *p* < 0.05 with
Mistral at the *p* = 0.050 boundary; transfer 12/13; judge κ = 0.287, IR recall 0.
