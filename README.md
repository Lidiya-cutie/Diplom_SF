# Дипломный проект: выбор региона для бурения скважин

**Автор:** Короткова Лидия Станиславовна  
**Курс:** SkillFactory  
**Тема:** машинное обучение в нефтедобыче — определение места бурения скважины

Репозиторий: [Lidiya-cutie/Diplom_SF](https://github.com/Lidiya-cutie/Diplom_SF)

---

## Бизнес-задача

1. Оценить запасы скважин моделью (официально — **только LinearRegression**).
2. Из пула 500 отобрать 200 лучших по прогнозу.
3. Бюджет 10 млрд ₽, выручка 450 тыс. ₽ / тыс. баррелей.
4. Решение по Bootstrap: средняя прибыль, 95% ДИ, риск убытков **< 2.5%**, плюс **CVaR 5%**.

## Данные и DVC/S3

Полные CSV (**100k×3**) версионируются через **DVC**, не через git.

| Артефакт | Назначение |
|----------|------------|
| `geo_data_*.csv.dvc` | указатели на полные датасеты |
| `data/samples/geo_data_*.csv` | 5k-сэмплы для CI/smoke (в git) |
| `data/DATA_CARD.md` | data card / DQ |

### Локальный remote + MinIO (S3-compatible)

AWS account в окружении может быть недоступен — рабочий S3-контур поднят на MinIO:

```bash
# 1) MinIO API :9100 / console :9101
bash scripts/start_minio.sh

# 2) DVC remotes: localremote (.dvc-storage) + minio (s3://diplom-sf/dvc)
bash scripts/setup_dvc.sh

# 3) Получить полные CSV
export AWS_ACCESS_KEY_ID=diplom_sf
export AWS_SECRET_ACCESS_KEY=diplom_sf_secret
export AWS_EC2_METADATA_DISABLED=true
dvc pull -r localremote   # или: dvc pull -r minio
```

Переключение на реальный AWS S3:

```bash
dvc remote add -f aws s3://<bucket>/diplom-sf
dvc remote modify aws region <region>
dvc push -r aws
```

## Структура

```
oilwells/           # CLI-пайплайн
scripts/            # start_minio.sh, setup_dvc.sh
data/samples/       # CI samples
artifacts/          # отчёты, dashboard.html, mlruns/ (gitignore)
geo_data_*.csv.dvc
oilwells.ipynb
theory/
```

## Установка

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.
```

Рекомендуемый venv на большой диск: `/mldata/venvs/diplom_sf`.

## CLI

```bash
# DQ
python -m oilwells dq --data-dir . --out-dir artifacts

# Официальный путь (LR) + sensitivity + CVaR + MLflow + dashboard
python -m oilwells run --data-dir . --out-dir artifacts --models lr

# Экспериментальное сравнение: LR vs ElasticNet vs HistGBR
python -m oilwells compare --data-dir . --out-dir artifacts

# CI smoke на samples
python -m oilwells smoke --data-dir data/samples --out-dir artifacts
```

MLflow UI:

```bash
mlflow ui --backend-store-uri ./artifacts/mlruns --port 5000
```

Дашборд: `artifacts/dashboard.html` (Plotly: прибыль, риск, распределения, CVaR).

## Модели

| kind | Статус | Назначение |
|------|--------|------------|
| `lr` | **official** | требование SkillFactory |
| `elasticnet` | experimental | регуляризация |
| `gbr` / `hgbr` | experimental | нелинейный бустинг |

Официальная рекомендация региона считается **только по `lr`**. Экспериментальные модели пишутся в leaderboard/MLflow с тегом `EXPERIMENTAL` (пример: `hgbr` на `region_2` часто проходит риск-гейт — сигнал исследовать нелинейность, не замена официальному выводу).

## Метрики решения

- RMSE / R² на valid  
- Bootstrap mean profit, 95% CI, P(loss)  
- Lift vs random baseline (200 случайных из 500)  
- **VaR 5% / CVaR 5%** по bootstrap-прибыли  
- Sensitivity: revenue/budget ×{0.8,1.0,1.2}, pool ∈{300,500,700}

## Канонические результаты (LR / full data)

| Регион | RMSE | Mean profit | Loss risk | CVaR5% | Gate |
|--------|------|-------------|-----------|--------|------|
| region_1 | ~0.89 | ~456 млн | ~1.5% | >0 | OK* |
| region_2 | ~40 | ~404 млн | ~7.6% | <0 | FAIL |
| region_0 | ~37.6 | ~396 млн | ~6.9% | <0 | FAIL |

\*DQ **critical** на `region_1` (дискретизация target + corr≈1 с `f2`) — формальный победитель с обязательным caveat.

## CI

`.github/workflows/oilwells-smoke.yml` — smoke на `data/samples` (LR+ElasticNet + assert DQ critical на region_1).

## Что реализовано

- [x] DVC + local remote + MinIO S3  
- [x] Samples в git для CI  
- [x] ElasticNet / HistGBR как experimental compare  
- [x] MLflow tracking  
- [x] CVaR/VaR + HTML dashboard  
- [x] Random baseline + sensitivity  

## Дальше (опционально)

- Прод-бакет AWS вместо MinIO  
- Калибровка прогноза объёма / conformal intervals  
- Онлайн MLflow server + auth
