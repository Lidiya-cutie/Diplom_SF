# Cloud Agent Starter Skill: run and test this repo

Use this as the default runbook for Cloud agents working in this repository.

## 1) First 5 minutes: practical setup

This codebase is a data-science project with Jupyter notebooks (`oilwells.ipynb`, `Linear regress_nums.ipynb`) and CSV datasets in repo root. There is no web app, no backend server, and no built-in login flow.

1. Confirm repository state:
   - `git status -sb`
   - `ls`
2. Use the existing virtual environment if present:
   - `source .venv/bin/activate`
3. Install baseline notebook/data stack if imports fail:
   - `python -m pip install --upgrade pip`
   - `python -m pip install jupyter nbconvert numpy pandas scikit-learn matplotlib seaborn`
4. Quick smoke command to confirm Python can import key libs:
   - `python -c "import numpy, pandas, sklearn; print('ok')"`

## 2) Cloud-agent quick facts (what is and is not applicable here)

- Login/auth: not applicable in this repo (no app auth flow).
- Feature flags: not applicable in this repo (no flag framework/config).
- App startup: there is no service to boot; execution means running notebooks.
- Main artifacts:
  - Data: `geo_data_0.csv`, `geo_data_1.csv`, `geo_data_2.csv`
  - Notebooks: `oilwells.ipynb`, `Linear regress_nums.ipynb`
  - Project context: `README.md`

If a future PR adds an app, auth, or flags, update this skill immediately with exact commands and test paths.

## 3) Codebase areas and concrete test workflows

### Area A: Data files in repo root (`geo_data_*.csv`)

Goal: verify input data exists, has expected shape, and is readable before notebook runs.

Run:
- `python - <<'PY'\nimport pandas as pd\nfor i in range(3):\n    p=f'geo_data_{i}.csv'\n    df=pd.read_csv(p)\n    print(p, df.shape, list(df.columns))\nPY`

What to check:
- Files load without exceptions.
- Columns include `id`, `f0`, `f1`, `f2`, `product`.
- Row counts are non-zero.

### Area B: Main analysis notebook (`oilwells.ipynb`)

Goal: execute notebook end-to-end in a non-interactive Cloud run and catch runtime issues.

Run:
- `jupyter nbconvert --to notebook --execute --inplace "oilwells.ipynb"`

Optional isolated output artifact:
- `jupyter nbconvert --to notebook --execute --output "oilwells.executed.ipynb" "oilwells.ipynb"`

What to check:
- Command exits with code 0.
- No Python traceback in output.
- Final notebook cells contain computed metrics/summary.

### Area C: Secondary notebook (`Linear regress_nums.ipynb`)

Goal: ensure educational/auxiliary notebook still executes after changes.

Run:
- `jupyter nbconvert --to notebook --execute --inplace "Linear regress_nums.ipynb"`

What to check:
- Command exits with code 0.
- No execution errors from sklearn/pandas/numpy imports and model cells.

### Area D: Quick regression check after notebook/data edits

Goal: run the fastest high-signal checks before opening/updating PR.

Run in order:
1. `python -c "import numpy, pandas, sklearn; print('imports-ok')"`
2. Dataset readability check from Area A.
3. Execute only notebook(s) touched by your diff via `nbconvert --execute`.

## 4) Common Cloud workflow patterns

- For notebook-only edits:
  - Prefer `nbconvert --execute` over manual UI execution.
  - Commit notebook output changes only if repository policy or task requires it.
- For data-file edits:
  - Re-run at least one dependent notebook section/end-to-end execution.
  - Validate schema/column consistency first (Area A command).
- For README/docs-only edits:
  - Confirm referenced files/commands still exist by running key commands once.

## 5) Troubleshooting run/test failures

- `ModuleNotFoundError`:
  - Activate `.venv` and install missing package with `python -m pip install <package>`.
- Notebook hangs:
  - Re-run with extended timeout:
    - `jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1200 --inplace "<notebook>.ipynb"`
- Kernel mismatch:
  - Install kernel into venv:
    - `python -m pip install ipykernel`
    - `python -m ipykernel install --user --name cloud-venv --display-name "Python (cloud-venv)"`
- `TypeError: LinearRegression.__init__() got an unexpected keyword argument 'normalize'` (in `oilwells.ipynb`):
  - Cause: notebook uses legacy sklearn argument removed in modern versions.
  - Fix notebook code by removing `normalize=False` from `LinearRegression(...)`.
  - Quick confirm before edit:
    - `rg "LinearRegression\\(normalize=" "oilwells.ipynb"`
- `OSError: 'seaborn' is not a valid package style` (in `Linear regress_nums.ipynb`):
  - Cause: old style alias is not available in newer matplotlib.
  - Fix notebook code by replacing `plt.style.use('seaborn')` with `plt.style.use('seaborn-v0_8')` (or remove the style line).
  - Quick confirm before edit:
    - `rg "plt\\.style\\.use\\('seaborn'\\)" "Linear regress_nums.ipynb"`

## 6) How to keep this skill updated

When you discover a new reliable command, workaround, or failure pattern:

1. Add it to the relevant Area section above (A/B/C/D) with:
   - exact command,
   - when to run it,
   - expected success signal.
2. If it is cross-cutting (applies to many changes), also add it to:
   - "First 5 minutes" (setup), or
   - "Troubleshooting run/test failures".
3. Keep entries minimal and executable (no vague advice, always command-first).
4. In PR description, include a one-line note: "Updated Cloud starter skill with new run/test runbook knowledge."
