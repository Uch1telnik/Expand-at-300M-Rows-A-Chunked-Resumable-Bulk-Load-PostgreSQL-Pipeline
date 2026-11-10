# How to upload this work to your GitHub repository

Repo folder on disk: `C:\Users\golub\Downloads\tsk\repo`
Remote already configured: `https://github.com/igorsiecz/kaggle_postgre_challenge.git`
Branch: `main`

Run the commands **on Windows in PowerShell** (Git Credential Manager is installed there,
so authentication uses a browser/popup instead of a token you have to paste).

---

## Step 0 — one-time identity (if commit fails with "Author identity unknown")

```powershell
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

Use the **same e-mail as your GitHub account** so the commit is attributed to you.

---

## Step 1 — go to the repo

```powershell
cd C:\Users\golub\Downloads\tsk\repo
```

Check you are on `main` and in sync:

```powershell
git status -sb
git branch -vv
```

Expected: `## main...origin/main`.

---

## Step 2 — make line endings consistent (fixes the "25 modified files" noise)

Your files were edited on Windows and are CRLF; the repo is LF. Without this step,
`git status` shows ~25 files as modified even though only one really changed.

```powershell
git add .gitattributes
git add --renormalize .
```

This stages LF versions of all tracked text files. It produces one large commit that
only changes line endings — that is expected and harmless.

---

## Step 3 — stage the new work

Everything in this one block (explicit list = no junk, no `.rar`, no `__pycache__`):

```powershell
git add optimized_pipeline.py
git add "SQL files optimized"
git add assets
git add results
git add WRITEUP.md SOLUTION.md KAGGLE_FIELDS.md make_assets.py
git add run_expansion_linux.py benchmark_variant.py
git add final_compare.sh test_recovery2.sh test_edge.sh bench_interleaved.sh check_table4.sh
git add bulkload.sql recreate_indexes.sql fused_record.sql typed_staging.sql explain_fused.sql
git add build_bulkload.py build_fused_record.py build_typed_staging.py build_optimized_recipes.py build_fused.py
git add services/postgres_service.py
```

Verify what will be committed *before* committing:

```powershell
git status --short
```

You should see only `A ` (added) and `M ` (modified) lines — no `??` junk, no `.rar`.

Optional: confirm the only real code change is the function-safety gate:

```powershell
git diff --cached --stat --ignore-cr-at-eol
```

Expected: `services/postgres_service.py | 6 +++---`.

---

## Step 4 — commit

```powershell
git commit -m "Expand optimization: chunked resumable bulk-load pipeline, writeup, assets, evidence"
```

---

## Step 5 — push

```powershell
git push origin main
```

First push will ask for authentication:

* **Browser popup** (Git Credential Manager) — sign in to GitHub and approve. Easiest.
* If asked in the terminal instead, use a **Personal Access Token** as the password:
  GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
  → grant **Contents: Read and write** on this repo. Paste the token when prompted
  for "Password".

---

## Step 6 — confirm

```powershell
git log --oneline -3
git status -sb
```

`## main...origin/main` with no ahead/behind marker means it is uploaded.

Open https://github.com/igorsiecz/kaggle_postgre_challenge and check the new files are there.

---

## If `git push` is rejected (`non-fast-forward`)

Someone else pushed meanwhile. Rebase and retry:

```powershell
git pull --rebase origin main
git push origin main
```

---

## What gets uploaded (and what does not)

**Uploaded (core):**

```
optimized_pipeline.py
services/postgres_service.py        (only real source change)
SQL files optimized/  (6 recipes)
assets/               (card_16x9, card_1x1, 3 gallery images)
results/              (bench / scale / recovery / edge logs)
WRITEUP.md  SOLUTION.md  KAGGLE_FIELDS.md  make_assets.py
run_expansion_linux.py  benchmark_variant.py
final_compare.sh  test_recovery2.sh  test_edge.sh  bench_interleaved.sh  check_table4.sh
bulkload.sql  recreate_indexes.sql  fused_record.sql  typed_staging.sql  explain_fused.sql
build_*.py  (generators for the SQL variants)
```

**Not uploaded (ignored or skipped):**

```
*.rar                  (already in .gitignore)
__pycache__/           (already in .gitignore)
the 2.6 GB generated database  (never commit; use generate_database.py to reproduce)
scratch duplicates: opt_err.txt, base1m.txt, fused1m.txt, opt1m_report.txt, opt_report.txt, ...
```

Total size of the upload is well under 2 MB — no GitHub limits are hit.

---

## WSL variant (only if you prefer Linux git)

The remote uses HTTPS, so it needs a token in WSL (no Credential Manager there):

```bash
cd /mnt/c/Users/golub/Downloads/tsk/repo
git config user.name  "Your Name"
git config user.email "you@example.com"
# same add/commit steps
git push origin main
# username: your GitHub username
# password: <personal access token>
```

---

## Security note (recommended before publishing)

The test/benchmark scripts contain the local sandbox passwords
(`challengepass`, `rootpass`) in plain text. If this repo is public, replace them
with environment variables, for example:

```bash
: "${PGPASSWORD:?set PGPASSWORD}"
```

Files that currently hardcode them:
`run_expansion_linux.py`, `bench_interleaved.sh`, `final_compare.sh`, `test_recovery2.sh`,
`test_edge.sh`, `check_table4.sh`, `benchmark_variant.py`, `SOLUTION.md`, `WRITEUP.md`.

Ask me and I will rewrite them to read `PGHOST/PGPORT/PGUSER/PGPASSWORD` from the
environment (with the same defaults documented in the README) before you push.
