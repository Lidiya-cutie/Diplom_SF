# Дипломный проект Коротковой Лидии Станиславовны для онлайн-школы SkillFactory

## Тема: Машинное обучение в нефтедобыче: определение места бурения скважины

**Описание исследования**

Допустим, вы работаете в добывающей компании «ГлавРосГосНефть».

Нужно решить, где бурить новую скважину.

Вам предоставлены пробы нефти в трёх регионах:

в каждом 10 000 месторождений, где измерили качество нефти и объём её запасов.

Необходимо построить модель машинного обучения, которая поможет определить регион, где добыча принесёт наибольшую прибыль.

Также необходимо проанализировать возможную прибыль и риски техникой Bootstrap.

**Шаги для выбора локации:**

В избранном регионе ищут месторождения, для каждого определяют значения признаков;

Строят модель и оценивают объём запасов;

Для обучения модели подходит только линейная регрессия (остальные — недостаточно предсказуемые).

Выбирают месторождения с самым высокими оценками значений.

Количество месторождений зависит от бюджета компании и стоимости разработки одной скважины;

Прибыль равна суммарной прибыли отобранных месторождений.

**Описание данных**

id — уникальный идентификатор скважины;

f0, f1, f2 — три признака точек (неважно, что они означают, но сами признаки значимы);

product — объём запасов в скважине (тыс. баррелей).

**Общий вывод**

Только второй регион подходит под условия задачи — риск убытков менее 2.5%.

Риск убытков во втором регионе — 1.5%.

Он же является регионом с наибольшей средней прибылью — 456 млн. руб.

Но исходя из выводов, сделанных при подготовке данных в начале исследования,
данные по объёму запасов второго региона:

имеют много (8%) нулевых значений;

11 уникальных значений объёма запасов выше нуля;

уникальные значения совпадают вплоть до восьмого знака после запятой.

Высока вероятность того, что данные по объёму запасов нарушены и им нельзя доверять.

Рекомендуется перепроверить источник данных по второму региону.
