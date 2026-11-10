# Push this project to YOUR OWN new GitHub repository

Current situation (important):

* `C:\Users\golub\Downloads\tsk\repo` is a **shallow clone** (1 commit) of
  `igorsiecz/kaggle_postgre_challenge`. Its only commit is authored by *igorsiecz*.
* Your Git identity is already set: `Uch1telnik <golubevyaroslavo@gmail.com>`.
* 62 files are staged and ready; nothing is committed yet.

Because the existing history belongs to someone else's repo, you have two options.
**Option A (recommended)** gives you a clean repository that is yours from the first
commit. **Option B** keeps the fork link to the original repo.

---

## Step 1 — create the empty repository on GitHub

1. Open https://github.com/new
2. **Repository name:** e.g. `kaggle-postgres-expand-optimization`
3. **Visibility:** Public (needed if you want judges to open it) or Private
4. **Do NOT** check "Add a README file", ".gitignore" or "license" — the repo must be
   completely empty, otherwise the first push is rejected.
5. Click **Create repository**.
6. Copy the HTTPS URL, e.g.
   `https://github.com/Uch1telnik/kaggle-postgres-expand-optimization.git`

> The URL must contain **your** username. The currently configured `origin` points to
> `igorsiecz/...` — that is not yours and you cannot push there.

---

## Option A — clean history in your own repo (recommended)

This drops the foreign 1-commit history and creates a fresh first commit authored by you.

### A.1 Remove the old git metadata

```powershell
cd C:\Users\golub\Downloads\tsk\repo
Remove-Item -Recurse -Force .git
```

`.git` holds only that one foreign shallow commit; **no source files are deleted**.

### A.2 Initialise a new repository

```powershell
git init -b main
git config user.name  "Uch1telnik"
git config user.email "golubevyaroslavo@gmail.com"
```

### A.3 Stage exactly the project files

```powershell
git add .gitattributes
git add optimized_pipeline.py
git add "SQL files optimized"
git add assets results
git add WRITEUP.md SOLUTION.md KAGGLE_FIELDS.md GITHUB_UPLOAD.md GITHUB_NEW_REPO.md make_assets.py
git add run_expansion_linux.py benchmark_variant.py
git add final_compare.sh test_recovery2.sh test_edge.sh bench_interleaved.sh check_table4.sh
git add bulkload.sql recreate_indexes.sql fused_record.sql typed_staging.sql explain_fused.sql
git add build_bulkload.py build_fused_record.py build_typed_staging.py build_optimized_recipes.py build_fused.py
git add services/postgres_service.py
```

The `.gitignore` already excludes `*.rar`, `__pycache__/` and scratch logs, so the
scratch files left in the folder will **not** be committed.

Check before committing:

```powershell
git status --short
```

Expected: only `A ` lines (plus `M` for nothing, since it is a fresh tree).
Should be ~64 files, no `.rar`, no `__pycache__`.

### A.4 Commit

```powershell
git commit -m "Expand optimization: chunked resumable bulk-load pipeline, writeup, assets, evidence"
```

### A.5 Attach YOUR repository and push

```powershell
git remote add origin https://github.com/Uch1telnik/YOUR-REPO-NAME.git
git push -u origin main
```

Replace `YOUR-REPO-NAME` with the name from Step 1.

Authentication: Git Credential Manager opens a browser window — sign in as
**Uch1telnik** and approve. If it asks in the terminal instead, paste a
**Personal Access Token** (GitHub → Settings → Developer settings → Personal access
tokens → Fine-grained tokens → Repository access: your new repo →
Permissions: Contents = Read and write) as the password.

### A.6 Verify

```powershell
git status -sb          # -> ## main...origin/main
git log --oneline -2    # -> your single commit
```

Open `https://github.com/Uch1telnik/YOUR-REPO-NAME` and confirm the files are there.

---

## Option B — keep the fork link to the original repo

If you want GitHub to show "forked from igorsiecz/kaggle_postgre_challenge", create the
new repo through **Fork** instead of "New":

1. Open https://github.com/igorsiecz/kaggle_postgre_challenge
2. Click **Fork** → owner = `Uch1telnik` → Create fork
3. Then in PowerShell:

```powershell
cd C:\Users\golub\Downloads\tsk\repo
git remote set-url origin https://github.com/Uch1telnik/kaggle_postgre_challenge.git
git commit -m "Expand optimization: chunked resumable bulk-load pipeline, writeup, assets, evidence"
git push origin main
```

Files are already staged in this case, so no re-adding is needed.

Downside: your first commit sits on top of a *shallow* foreign history, so the repo
shows igorsiecz's commit as the parent. Option A avoids that.

---

## Common problems

**`remote origin already exists`**
```powershell
git remote set-url origin https://github.com/Uch1telnik/YOUR-REPO-NAME.git
```

**`Updates were rejected because the remote contains work you do not have`**
The new repo was not empty. Either delete it and recreate empty, or:
```powershell
git pull --rebase origin main
git push -u origin main
```

**`Authentication failed`**
Your cached credential is for another account. Clear it and retry:
```powershell
cmdkey /list | findstr github
cmdkey /delete:git:https://github.com
git push -u origin main
```

**`Author identity unknown`**
```powershell
git config user.name  "Uch1telnik"
git config user.email "golubevyaroslavo@gmail.com"
```

**`src refspec main does not match any`**
The commit did not happen. Run `git status`, then `git commit` again.

---

## What is uploaded

Core (~64 files, < 2 MB):

```
optimized_pipeline.py
services/postgres_service.py            (only real source change)
SQL files optimized/                    (6 recipes)
assets/                                 (cards + gallery)
results/                                (benchmark / recovery evidence)
WRITEUP.md  SOLUTION.md  KAGGLE_FIELDS.md  GITHUB_UPLOAD.md  GITHUB_NEW_REPO.md
make_assets.py  run_expansion_linux.py  benchmark_variant.py
final_compare.sh  test_recovery2.sh  test_edge.sh  bench_interleaved.sh  check_table4.sh
bulkload.sql  recreate_indexes.sql  fused_record.sql  typed_staging.sql  explain_fused.sql
build_*.py
```

Not uploaded: `*.rar`, `__pycache__/`, the 2.6 GB generated database (reproduce with
`generate_database.py`), and scratch duplicates.

---

## Security note before publishing

These files contain the local sandbox passwords (`challengepass`, `rootpass`) in plain
text: `run_expansion_linux.py`, `bench_interleaved.sh`, `final_compare.sh`,
`test_recovery2.sh`, `test_edge.sh`, `check_table4.sh`, `benchmark_variant.py`,
`SOLUTION.md`, `WRITEUP.md`.

For a **public** repo, replace them with environment variables, e.g.

```bash
: "${PGPASSWORD:?set PGPASSWORD}"
```

Ask and I will rewrite them to read `PGHOST/PGPORT/PGUSER/PGPASSWORD` from the
environment before you push.
