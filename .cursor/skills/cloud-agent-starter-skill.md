# Cloud Agent Starter Skill: Oil Wells ML Notebooks

Use this skill when a Cloud agent is new to this repository and needs fast, reliable setup + test steps.

## 1) Repo-wide bootstrap (run first)

### Login and identity checks
- Confirm GitHub CLI auth (for reading PR/CI context):
  - `gh auth status`
- Confirm you are in repo root:
  - `pwd`
  - `git status`

### Python environment
This repo ships with a local virtual env (`.venv`) and notebook-first workflow.

- Preferred interpreter:
  - `./.venv/bin/python --version`
- If `.venv` is missing, create and install minimum dependencies:
  - `python3 -m venv .venv`
  - `./.venv/bin/pip install --upgrade pip`
  - `./.venv/bin/pip install jupyter pandas numpy matplotlib seaborn scikit-learn`

## 2) Codebase area: data files (`geo_data_*.csv`)

### What this area contains
- Three source datasets used by notebooks:
  - `geo_data_0.csv`
  - `geo_data_1.csv`
  - `geo_data_2.csv`

### Practical test workflow
Run a schema + null smoke check before notebook execution:

- `./.venv/bin/python -c "import pandas as pd; files=['geo_data_0.csv','geo_data_1.csv','geo_data_2.csv']; [print(f, pd.read_csv(f).shape, pd.read_csv(f).isna().sum().sum()) for f in files]"`

Expected: each file loads successfully, shape is `(100000, 5)`, null count is `0`.

## 3) Codebase area: `oilwells.ipynb`

### Start the app (notebook server)
Use Jupyter Notebook as the runtime "app":

- `./.venv/bin/jupyter notebook --no-browser --ip=0.0.0.0 --port 8888`

### Practical test workflow
Prefer quick deterministic smoke checks in Cloud runs:

- `./.venv/bin/python -c "import pandas as pd; from sklearn.model_selection import train_test_split; from sklearn.linear_model import LinearRegression; from sklearn.metrics import mean_squared_error; d=pd.read_csv('geo_data_0.csv'); X=d[['f0','f1','f2']]; y=d['product']; Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.25,random_state=12345); m=LinearRegression().fit(Xtr,ytr); p=m.predict(Xte); print('rmse', mean_squared_error(yte,p)**0.5)"`

Optional full notebook execution:

- `./.venv/bin/jupyter nbconvert --to notebook --execute --inplace "oilwells.ipynb"`

## 4) Codebase area: `Linear regress_nums.ipynb`

### Practical test workflow
- Import smoke test for notebook dependencies:
  - `./.venv/bin/python -c "import numpy, pandas, matplotlib, seaborn, sklearn; print('ok')"`
- Optional full notebook execution:
  - `./.venv/bin/jupyter nbconvert --to notebook --execute --inplace "Linear regress_nums.ipynb"`

## 5) Feature flags / mocks in Cloud runs

This repository has no built-in runtime feature-flag framework. Use execution-level "mock" controls to keep runs stable:

- Use row sampling for fast validation:
  - `./.venv/bin/python -c "import pandas as pd; d=pd.read_csv('geo_data_0.csv').sample(2000, random_state=12345); print(d.shape)"`
- Keep all random behavior deterministic with `random_state=12345`.

If a future task introduces real feature flags, document:
- Exact env var name(s)
- Default value(s)
- Safe Cloud test value(s)
- One command that proves the flag path is active

## 6) Common Cloud workflow steps

- Create a work branch:
  - `git checkout -b cursor/<short-task-name>`
- Commit + push after each validated change set:
  - `git add <files>`
  - `git commit -m "<clear message>"`
  - `git push -u origin <branch>`

## 7) Keep this skill updated (runbook hygiene)

Whenever a new setup fix or testing trick is discovered:
1. Add it to the relevant area section above (data / notebook / workflow).
2. Include one copy/paste command and expected output signal.
3. Mark whether it is **required** or **optional**.
4. Remove stale steps that no longer work in Cloud.
5. In the PR description, mention: "Updated starter skill runbook" so future agents can find it quickly.
