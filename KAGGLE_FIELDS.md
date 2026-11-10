# Kaggle Writeup — field-by-field filling guide

Paste the blocks below into the matching Kaggle fields. Everything is written in
English to match the competition and the report language.

---

## 1) Title

```
Expand at 300M Rows: A Chunked, Resumable, Bulk-Load PostgreSQL Pipeline
```

Shorter alternative (if a char limit bites):

```
Chunked, Resumable Bulk-Load Expansion for 300M JSONB Rows
```

---

## 2) Subtitle (one sentence)

```
Rewriting the JSONB Expand from six full scans in one transaction into a
single-parse, natural-key, bulk-loaded pipeline that runs ~3.3x faster with
constant 22 MB memory and resumes from any crash.
```

One-line variant:

```
A chunked, checkpointed, bulk-load rewrite of the JSONB Expand that is ~3.3x
faster, memory-flat, and crash-resumable.
```

---

## 3) Card and Thumbnail Image

Two exact-ratio versions are provided — everything is inside the frame, nothing
is cropped:

- **16:9 (1280×720)** → `assets/card_16x9.png` (or `assets/card_16x9.jpg`)
- **1:1 (1080×1080)** → `assets/card_1x1.png` (or `assets/card_1x1.jpg`)

Use the 16:9 as the Kaggle Card/Thumbnail (that is the slot's ratio). Keep the
1:1 for the competition gallery, social preview, or any square placement.
JPEG copies are provided in case the uploader rejects PNG.

---

## 4) Media gallery

Upload in this order (they read as a story). All three are **16:9 (1280×720)**:

1. `assets/gallery_benchmark.png` — baseline vs optimized measured totals
2. `assets/gallery_memory.png` — constant RSS across chunk sizes
3. `assets/gallery_architecture.png` — chunk transaction / checkpoint design

Optional caption for each:
- "1M rows: 198.8 s baseline -> ~60 s optimized (interleaved A/B)."
- "Peak client RSS = 21.9 MB at 50k / 200k / 500k chunks."
- "Each chunk is one transaction; the checkpoint commits with the data."

---

## 5) Project Description

Paste the full Markdown from `WRITEUP.md`. Kaggle renders GitHub-flavoured
Markdown (headings, tables, fenced code), so it should display as intended.
If tables render poorly in the editor preview, keep them — they render on the
published page.

Structure it is already written in:
1. Problem statement
2. Measured bottlenecks
3. Strategy (SQL rewrite, bulk-load, chunk+checkpoint)
4. Results (speed, correctness, recovery, storage)
5. Scaling to 300M rows
6. What was deliberately kept
7. Reproduce
8. Lessons

---

## 6) Attachments (links to code / demos / Kaggle files)

Add these links (adjust to what you actually publish):

- Code (GitHub repo):
  `https://github.com/igorsiecz/kaggle_postgre_challenge`
- Main pipeline file (direct link):
  `https://github.com/igorsiecz/kaggle_postgre_challenge/blob/main/optimized_pipeline.py`
- Kaggle Dataset (generated database, optional if you upload one):
  `https://www.kaggle.com/datasets/<your-username>/<dataset-slug>`

If you do not want to publish the whole repo, attach only:
- `optimized_pipeline.py`
- `SQL files optimized/` (six recipes)
- `final_compare.sh`, `test_recovery2.sh`, `test_edge.sh`
- the six files under `results/` used as evidence

---

## 7) Files (upload, max 100 MB)

Recommended upload set (small, well under 100 MB):

```
optimized_pipeline.py
WRITEUP.md
SOLUTION.md
SQL files optimized/ (6 .sql files)
final_compare.sh
test_recovery2.sh
test_edge.sh
bench_interleaved.sh
results/ (bench + scale + recovery logs)
assets/card_16x9.png
assets/card_1x1.png
assets/gallery_benchmark.png
assets/gallery_memory.png
assets/gallery_architecture.png
```

Do **not** upload the generated 2.6 GB database or `raw_data`; if you want it
reproducible, publish it as a Kaggle Dataset and link it in Attachments.

Zip suggestion if the uploader only takes single files:

```
kaggle_writeup_bundle.zip
├─ optimized_pipeline.py
├─ WRITEUP.md
├─ SOLUTION.md
├─ SQL files optimized/
├─ scripts/ (final_compare.sh, test_recovery2.sh, test_edge.sh, bench_interleaved.sh)
├─ results/
└─ assets/
```

---

## 8) DOI Citation

Enable it. The writeup is a self-contained technical report with reproducible
commands and measured results, so a DOI is appropriate and makes it citable.
No extra action needed beyond toggling the option on.

---

## Before you publish — checklist

- [ ] `card_16x9.png` uploaded as the card/thumbnail (`card_1x1.png` kept for square placements).
- [ ] All three gallery images uploaded, in order.
- [ ] `WRITEUP.md` pasted into Project Description; preview tables render.
- [ ] GitHub link works and `optimized_pipeline.py` is committed/pushed.
- [ ] Attachments include the code link (and dataset link if published).
- [ ] Files include the pipeline, recipes, scripts, results, and assets.
- [ ] DOI citation enabled.
- [ ] Numbers quoted match the logged evidence in `results/`:
      baseline `198.75 s`, optimized `58.4–68.6 s`, RSS `22 MB`,
      semantic diff `0`, recovery `0 dup / 0 missing / 0 FK violations`.

---

## Optional: if you also run the 10M dataset

If you generate 10M rows before publishing, add one line to section 4.1 and a
scaling row to section 5, using:

```bash
export PG_KAGGLE_CHALLENGE_PASS='<postgres-password>'
python3 generate_database.py \
  --rows 10000000 --replace --host 127.0.0.1 --postgres_port 5433 \
  --user challenge --admin_database postgres
```

Then rerun `bench_interleaved.sh`-style A/B and record:
`baseline X s · optimized Y s · peak RSS Z MB`. The architecture does not change;
only the per-row scaling constant does.
