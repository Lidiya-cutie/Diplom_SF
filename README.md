# Дипломный проект: выбор региона для бурения скважин

**Автор:** Короткова Лидия Станиславовна  
**Курс:** SkillFactory  
**Тема:** машинное обучение в нефтедобыче — определение места бурения скважины

Репозиторий: [Lidiya-cutie/Diplom_SF](https://github.com/Lidiya-cutie/Diplom_SF)

---

## Бизнес-задача

Компания «ГлавРосГосНефть» выбирает регион для разработки:

1. В регионе исследуют скважины и измеряют признаки.
2. Модель оценивает объём запасов (`product`, тыс. баррелей). По условию задачи допускается **только линейная регрессия**.
3. Из 500 кандидатов отбирают **200** скважин с лучшим прогнозом.
4. Бюджет разработки — **10 млрд ₽**; выручка — **450 тыс. ₽** за тыс. баррелей.
5. Решение принимают по **Bootstrap**: средняя прибыль, 95% ДИ, риск убытков **< 2.5%**.

Подробности Bootstrap: [статья ODS на Хабре](https://habr.com/ru/companies/ods/articles/324402/).

## Данные

| Файл | Ключ | Скважин |
|------|------|---------|
| [`geo_data_0.csv`](geo_data_0.csv) | `region_0` | 100 000 |
| [`geo_data_1.csv`](geo_data_1.csv) | `region_1` | 100 000 |
| [`geo_data_2.csv`](geo_data_2.csv) | `region_2` | 100 000 |

Признаки: `id`, `f0`, `f1`, `f2`, `product`. Data card: [`data/DATA_CARD.md`](data/DATA_CARD.md).

### Качество данных

Автоаудит: `python -m oilwells dq` → `artifacts/dq_report.json`.

- `region_1`: ~12 уникальных `product`, ~8% нулей, corr(`f2`,`product`) ≈ **0.999** → severity **critical**.
- Во всех файлах есть дубликаты `id` (политика задаётся CLI, по умолчанию `keep_all`).

## Структура

```
Diplom_SF/
├── oilwells/                 # воспроизводимый пайплайн (CLI)
│   ├── dq.py                 # DQ-аудит
│   ├── model.py              # LinearRegression + metrics
│   ├── profit.py             # bootstrap + random baseline
│   ├── sensitivity.py        # чувствительность к цене/бюджету/пулу
│   └── pipeline.py / cli.py
├── oilwells.ipynb            # исследовательский ноутбук
├── geo_data_*.csv
├── data/DATA_CARD.md
├── requirements.txt
├── .github/workflows/oilwells-smoke.yml
└── theory/                   # учебный GD/SGD (Boston), вне бизнес-расчёта
```

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.

# DQ-аудит
python -m oilwells dq --data-dir . --out-dir artifacts

# Полный прогон: модель, bootstrap, random baseline, sensitivity
python -m oilwells run --data-dir . --out-dir artifacts

# Быстрый CI smoke
python -m oilwells smoke --data-dir . --out-dir artifacts --subsample 8000

# Ноутбук
jupyter notebook oilwells.ipynb
```

Политика дубликатов id: `--dup-id-policy keep_all|drop_keep_first|drop_keep_last`.

Артефакты: `artifacts/dq_report.json`, `pipeline_report.json`, `leaderboard.csv`, `smoke_report.json`.

## Методика

| Этап | Реализация |
|------|------------|
| Split | 75/25, `random_state=12345` |
| Scaling | `StandardScaler` fit только на train |
| Модель | `LinearRegression` (ограничение задачи) |
| Метрики | RMSE, R² |
| Bootstrap | 1000× pool=500 → top-200 по прогнозу; profit по факту; sampling через **iloc** |
| Baseline | тот же bootstrap, но 200 скважин **случайно** из пула |
| Sensitivity | сетка revenue/budget ×{0.8,1.0,1.2}, pool ∈{300,500,700} |
| Риск-гейт | P(profit < 0) < 2.5% |

## Результаты (канонический прогон)

| Регион | RMSE | Bootstrap ср. прибыль | Риск | vs random (lift) | Гейт |
|--------|------|----------------------|------|------------------|------|
| `region_1` | ~0.89 | ~456 млн ₽ | ~1.5% | ≫ 0 | OK* |
| `region_2` | ~40.0 | ~404 млн ₽ | ~7.6% | ≫ 0 | FAIL |
| `region_0` | ~37.6 | ~396 млн ₽ | ~6.9% | ≫ 0 | FAIL |

\*Формальный победитель по условию задачи, но **DQ critical** — без аудита источника не использовать как единственное бизнес-решение.

Модель даёт большой lift относительно случайного отбора: случайные 200 из 500 в среднем ниже порога безубыточности (~111 тыс. барр.), поэтому baseline убыточен, а ранжирование по LR окупается.

Sensitivity: доля прогонов сетки с прохождением риск-гейта выше у `region_1`, но заметно падает при ухудшении revenue/budget — решение неустойчиво к экономике проекта.

## CI

GitHub Actions: `.github/workflows/oilwells-smoke.yml` — `python -m oilwells smoke` на subsample + assert, что `region_1` помечен critical в DQ.

## Что уже закрыто из roadmap

- [x] Автоматический DQ-аудит `geo_data_1` + JSON-отчёт  
- [x] Явная политика дубликатов `id`  
- [x] Sensitivity по цене / бюджету / размеру пула  
- [x] Random baseline 200 из 500  
- [x] Пакет `oilwells/` + CLI + JSON/CSV артефакты  
- [x] CI smoke  

## Дальнейшие улучшения (вне текущего scope)

1. DVC/S3 для CSV вместо хранения только в git  
2. Если снимут ограничение «только LR» — ElasticNet/бустинг + калибровка объёма  
3. CVaR / opportunity-cost дашборд  
4. MLflow-логирование распределений bootstrap  

## Теория

[`theory/linear_regression_numerical.ipynb`](theory/linear_regression_numerical.ipynb) — численное решение LR (GD/SGD на Boston). К нефтяному расчёту не подключено.
