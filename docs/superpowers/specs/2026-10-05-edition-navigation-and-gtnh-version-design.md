# Дизайн: backButton на выборе языка и GTNH-сценарий выбора версии

Дата: 2026-10-05
Ветка: `gtnh-edition`

## 1. Контекст и мотивация

После интеграции edition-архитектуры стартовый поток выглядит так
(`src/main.py:41-53` → `controllers/Scenarios/__init__.py:38-46`):

`chooseEdition` → `routeStartup` → `chooseLanguage` → `enroll` →
`configureThaumWindowCoords` → `chooseThaumVersion` → `beReadyForCreatingTI`.

Проблемы:

1. Экран выбора языка (`scenario0_Language.chooseLanguage`) не имеет кнопки «назад»,
   поэтому, выбрав режим и попав на выбор языка, пользователь не может вернуться и
   сменить edition (GTNH ↔ Vanilla) без перезапуска/ручной правки конфига.
2. GTNH-режим использует дефолтный `scenario4_ChooseThaumVersion`, который строит список
   из `AppState.allAspectRecipes`. Для GTNH это объединение ванильных версий мода
   (`4.1.0g - 4.1.1.8`, …) и ключа `"GTNH"`, то есть выбор предлагается по версии мода
   Thaumcraft. В GTNH выбирать нужно по версии сборки, а не мода.

Текущее происхождение списка версий (для справки): `AppState.rereadThaumVersion`
(`src/utils/AppState.py:102-103`) объединяет базовый `configs/aspects_configs/aspectsRecipes.json`
с `edition.extraAspectRecipes()`; у `GtnhEdition` это
`src/gtnh/data/aspects_configs/gtnhAspectsRecipes.json` с единственным ключом `"GTNH"`.

## 2. Цели

- Дать возможность сменить edition с экрана выбора языка через кнопку «назад».
- Сделать так, чтобы GTNH-режим показывал **свои** кнопки выбора версии (по версии
  сборки), а не версии мода Thaumcraft.
- Не менять поведение vanilla-режима.
- Не дублировать дефолтный сценарий выбора языка; GTNH-сценарий 4 — изолированная копия
  (решение пользователя: вариант «A: отдельная копия»).

## 3. Часть 1 — backButton на экране выбора языка

Файл: `src/controllers/Scenarios/scenario0_Language.py`.

Изменения в `chooseLanguage(UI)`:

- В вызов `createNextBackButtonsAndText` передать back-callback:
  `Scenarios.chooseEdition` с аргументами `[UI]`.
- Текст кнопки задать явно литералом `overrideBackText="< Back"`. Причина: экран выбора
  языка открывается до сохранения языка, поэтому `AppState.translatedTexts` пуст и
  обращение к `TEXTS.Buttons.backArrowed` внутри
  `createNextBackButtonsAndText` (`shared.py:90`) привело бы к `KeyError`. По той же
  причине уже задан литерал `"Go next >"`.
- Сменить распаковку результата с `(infoText, nextButton, _)` на
  `(infoText, backButton, nextButton)`. В `createNextBackButtonsAndText`
  (`shared.py:102`) порядок элементов — `[mainText, back, next]`, поэтому при наличии
  back второй элемент — кнопка «назад», третий — «далее». Позиционирование списка языков
  (`updateTextsPosition`) продолжает использовать `nextButton.y`/`nextButton.h`.

Поведение:

- «Назад» (и клавиша `Backspace`, которую вешает `shared.py:94`) → `Scenarios.chooseEdition(UI)`.
- `chooseEdition` вызывает `UI.clearAll()`, который очищает `keysCallbacks` (в т.ч.
  backspace), поэтому «залипших» хендлеров не остаётся.
- «Далее» в `chooseEdition` → `saveEdition` + `activateEdition` + `routeStartup`; язык ещё
  не сохранён, поэтому `routeStartup` снова открывает `chooseLanguage` уже с другой edition.
- Смена edition корректна на лету: `activateEdition` → `rereadAllConfigs` сбрасывает
  несовместимую версию (`AppState.validVersionKeys`) и подхватывает свои window-controls
  (у режимов раздельные файлы контролов). Выбранный язык при возврате не сбрасывается.

## 4. Часть 2 — GTNH-специфичный сценарий 4

Решение: отдельная полная копия дефолтного сценария 4, с тремя отличиями (источник
списка версий, заголовок и версия по умолчанию). Изоляция важнее устранения ~100 строк
дублирования.

### 4.1. Подменяемость сценария 4

Файл: `src/controllers/Scenarios/__init__.py`.

- В `_DEFAULT_SCENARIOS` (строка 14) добавить запись
  `"chooseThaumVersion": chooseThaumVersion`.
- Это позволяет `applyEdition` подменять сценарий 4 и валидировать override.
- Никакие другие изменения в core не вносятся; для vanilla дефолтная реализация остаётся.

### 4.2. Новый модуль `src/gtnh/scenarios/scenario4_ChooseThaumVersion.py`

Полная копия `controllers/Scenarios/scenario4_ChooseThaumVersion.py` со следующими
отличиями:

- Список версий: `versions = getGtnhVersions()` из `gtnh` (см. 4.3) вместо
  `list(AppState.allAspectRecipes.keys())`.
- Заголовок: `AppState.translatedTexts[TEXTS.chooseGtnhVersion]` вместо
  `TEXTS.chooseThaumVersion`.
- Версия по умолчанию: `"GTNH"` вместо `"4.2.2.0 - 4.2.3.5"` (иначе при единственном
  пункте `"GTNH"` ничего не было бы подсвечено).
- Всё остальное идентично дефолту: `onSubmit` вызывает `AppState.saveThaumVersion(...)` и
  `Scenarios.beReadyForCreatingTI(UI)`; back — `Scenarios.configureThaumWindowCoords, [UI]`;
  подсветка ранее выбранной версии из `AppState.selectedThaumVersion`; сеточная раскладка.
- Функция экспортируется как `chooseThaumVersion(UI)`.

Выбранная версия (`"GTNH"`) проходит валидацию в `AppState.rereadThaumVersion`, так как
`GtnhEdition.validVersionKeys()` возвращает `{"GTNH"}`, а ключ присутствует в
`allAspectRecipes`.

### 4.3. Helper версий GTNH

Файл: `src/gtnh/__init__.py`.

- Добавить функцию `getGtnhVersions() -> list[str]`, возвращающую
  `list(createEdition().extraAspectRecipes().keys())` (сейчас `["GTNH"]`). Источник —
  именно рецепты GTNH, а не объединённый `allAspectRecipes`.
- В `GtnhEdition.scenarioOverrides` (строка 23) добавить
  `"chooseThaumVersion": chooseThaumVersion` (ленивый импорт из
  `gtnh.scenarios.scenario4_ChooseThaumVersion`).

### 4.4. Тексты

Файл: `configs/translations.py`.

- Добавить ключ `TEXTS.chooseGtnhVersion = "chooseGtnhVersion"`.
- Добавить перевод во все 11 языков:

| Язык | Текст |
|---|---|
| Russian | Выберите версию сборки GTNH. |
| English | Choose the GTNH modpack version. |
| Italian | Scegli la versione della modpack GTNH. |
| Dutch | Kies de GTNH-modpackversie. |
| Spanish | Elige la versión del modpack de GTNH. |
| Arabic | اختر إصدار تجميعة GTNH. |
| Chinese (Traditional) | 選擇 GTNH 整合包版本。 |
| Chinese (Simplified) | 选择 GTNH 整合包版本。 |
| French | Choisissez la version du modpack GTNH. |
| Hindi | GTNH मॉडपैक संस्करण चुनें। |
| Korean | GTNH 모드팩 버전을 선택하세요. |

### 4.5. Подмена в рантайме

Все вызовы идут через атрибут пакета `Scenarios.chooseThaumVersion`
(`scenario3:33`, `scenario6:35,41`, `scenario7:27`, `scenario8:371`) либо через
module-global в `routeStartup` (`__init__.py:44`). `applyEdition` присваивает новые
функции в `globals()` пакета, поэтому обе формы вызова получают GTNH-реализацию.

## 5. Тесты

- `tests/test_translations.py`: включить `TEXTS.chooseGtnhVersion` в
  `test_new_edition_texts_are_translated` (проверка непустоты и наличия перевода во всех
  языках). Существующий `test_all_languages_have_all_texts` автоматически проверяет
  наличие ключа во всех языках.
- `tests/test_gtnh_edition.py`: `getGtnhVersions()` возвращает `["GTNH"]` (импорт
  `gtnh` не тянет PyQt).
- UI-поток (back-кнопка, содержимое кнопок GTNH-сценария 4) юнит-тестами не покрывается:
  в WSL-окружении нет PyQt5, а модуль сценария импортирует `PyQt5`. Проверка вручную на
  Windows (см. раздел 7).

## 6. Вне области работ

- Добавление нескольких версий сборки GTNH (сейчас одна — `"GTNH"`).
- Изменение дефолтного сценария 4 для vanilla.
- Рефакторинг `createNextBackButtonsAndText` и исправление неочевидного порядка возврата
  `(mainText, back, next)`.
- Изменение `AppState`/валидации версий.

## 7. Ручная проверка (Windows)

1. Первый запуск (пустые конфиги): выбрать `GTNH` → на экране языка нажать «Назад» →
   выбрать `Vanilla` → «Далее» → снова экран языка (язык не сброшен) → продолжить.
2. Клавиша `Backspace` на экране языка ведёт на выбор edition.
3. Повторный выбор той же edition: поток не ломается, возврат на язык.
4. GTNH-режим: сценарий 4 показывает единственную кнопку `GTNH`, заголовок
   локализован; выбор `GTNH` → `beReadyForCreatingTI`.
5. Vanilla-режим: сценарий 4 без изменений — список версий мода Thaumcraft.
6. Обычный запуск с уже заполненными конфигами не затронут.
