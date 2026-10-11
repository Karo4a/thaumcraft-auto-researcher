# Дизайн: расстановка аннотаций типов в `src/` и `configs/`

Дата: 2026-10-11
Ветка: `master`

## 1. Контекст и мотивация

В проекте типизация уже частично присутствует: образцовые модули
(`src/editions/base.py`, `src/controllers/Aspect.py`, `src/utils/AppState.py`,
`_Object.render`) аннотированы, но значительная часть кода — нет (например,
`src/controllers/Point.py`, `src/UI/primitives/Image.py`,
`src/controllers/Scenarios/scenario8_Researchings.py`, большинство методов
`src/UI/OverlayUI.py`). Смешанное состояние ухудшает читаемость, автодополнение
в IDE и регрессионную защиту.

Цель — привести аннотации к единому стандарту во всей production-части
(`src/` + `configs/`), не меняя поведение приложения.

## 2. Область и ограничения

**Входит в область:**

- Каталоги `src/` и `configs/`.
- Аннотации параметров функций/методов (кроме `self`/`cls`).
- Аннотации возвращаемых типов (включая `-> None` для `void`).
- Аннотации атрибутов классов и модульных переменных.

**Не входит в область:**

- Каталоги `tests/` и `scripts_other/` (решение пользователя).
- Аннотации локальных переменных внутри тел функций.
- Тип-чекер (mypy/pyright) и его CI-интеграция (решение пользователя).
- Пакеты-стабы для внешних библиотек (`PyQt5-stubs`, `types-Pillow` и т.п.).
- Любые изменения логики, переименования, рефакторинг сигнатур.

## 3. Текущее состояние (метрики)

| Метрика | Значение |
|---|---|
| Файлов с пропусками | 46 |
| Функций всего / требуют работы | 372 / **309** |
| Пропущено аннотаций параметров | **221** |
| Пропущено аннотаций возврата | **303** |
| Неаннотированных атрибутов классов | **73** |
| Неаннотированных модульных переменных | **66** |

Топ файлов по объёму работ:

| Файл | Функций (требуют/всего) | Атрибуты | Модульные |
|---|---|---|---|
| `src/UI/OverlayUI.py` | 50/55 | 10 | 2 |
| `src/controllers/ThaumInteractor.py` | 32/43 | 3 | 0 |
| `src/controllers/Scenarios/scenario8_Researchings.py` | 27/27 | 0 | 0 |
| `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py` | 21/21 | 0 | 0 |
| `src/logic/LinksGeneration.py` | 17/18 | 0 | 1 |
| `src/controllers/Scenarios/scenario7_DetectionAspectsDialogue.py` | 14/14 | 0 | 0 |
| `src/utils/LinkableValue/LinkableValue.py` | 13/14 | 0 | 0 |
| `src/utils/AppState.py` | 13/13 | 0 | 1 |
| `configs/translations.py` | 0/0 | 36 | 1 |
| `configs/constants.py` | 3/3 | 0 | 39 |

## 4. Стандарт аннотаций

1. **Объединения** — PEP 604: `X | None`, без `Optional`.
2. **Дженерики** — встроенные: `list[str]`, `dict[str, dict[str, str]]`,
   `tuple[int, int]`, `set[str]`.
3. **Колбэки** — `Callable[[...], ...]` из `typing`; для вариативных сигнатур —
   `Callable[..., Any]`.
4. **Forward references** — строкой, как в `src/editions/__init__.py:13`
   (`"BaseEdition | None"`). `from __future__ import annotations` не добавляем.
5. **Неизвестные/динамические внешние типы** — `Any`. External-пакеты
   (`PyQt5`, `keyboard`, `mouse`, `appdata`, `onnxruntime`) без стабов, поэтому
   там, где тип неочевиден, — `Any`; где очевиден — конкретный тип
   (`QColor`, `Image.Image`, `np.ndarray`).
6. **`*args`/`**kwargs`** — `*args: Any, **kwargs: Any` (конкретизируем, только
   если элемент один и его тип ясен).
7. **`void`** — всегда `-> None`.
8. **Стиль имён** — сохраняем существующий `camelCase`; комментарии не добавляем.
9. **Локальные переменные не аннотируем.**

## 5. Особые случаи (критично)

1. **`configs/translations.py`** — `TEXTS` и `TEXTS.Buttons` объявлены как
   `@dataclass`. Аннотация обычным `field: str = ...` превратит их в поля
   dataclass и изменит `__init__`. Использовать **`ClassVar[str]`** из `typing`.
   `TRANSLATIONS` — `dict[str, dict[str, str]]`.
2. **Члены `Enum`** (`KeyboardKeys`) **не аннотировать** — аннотация ломает
   распознавание члена перечисления.
3. **`_Object`**: значения по умолчанию в базовом классе + динамика через
   `getattr(self, targetFieldName)`. Типы: `lineWidth: int`,
   `color: QColor`, `hoverColor: QColor | None`,
   `onClickCallback: Callable | None`, `onClickCallbackArgs: list[Any]`,
   `clickable: bool`, `movable: bool`, `hoverable: bool`, `visible: bool`.
4. **`Singleton._instances`** (`src/utils/utils.py`) и
   **`Neurolink._instances`** — `dict[type, Any]`.
5. **`_objectIdValue = itertools.count()`** — `Iterator[int]` (в Python 3.10
   рантайм-подписка `count[int]` запрещена).
6. **PyQt**: сигналы (`pyqtSignal()`) — `Any` или конкретный тип сигнала;
   переопределения событий (`paintEvent`, `mousePressEvent`, `mouseMoveEvent`,
   `mouseReleaseEvent`, `timerEvent`) — по типам Qt (`QtGui.QPaintEvent`,
   `QtGui.QMouseEvent`, `QTimerEvent`) и `-> None`.
7. **`gtnh/controls.py::saveGtnhThaumWindowControls`** и
   **`AppState._saveVanillaThaumWindowControls`** — точечные аргументы имеют
   `LinkableCoord` (обращение к `.x`/`.y`); `hexagonSlotSizeY` — `float`/`int`.
   Конкретный тип уточняется по месту.
8. **`LinkableValue`** dunder-методы: `other: LinkableValue | float`,
   возвраты — `float | LinkableValue`; `val: float`. `editLinkableValue` уже
   аннотирован `Union` — привести к `LinkableValue | float` для единообразия.
9. **`base.py` / `gtnh/__init__.py` `saveThaumWindowControls(self, *args, **kwargs)`**
   — `*args: Any, **kwargs: Any`.
10. **callback-контейнеры** в `OverlayUI` — `tuple[Callable, list[Any]]` в
    элементах `list`/`dict`.

## 6. План выполнения (батчи)

Порядок — от листовых модулей к зависимым. После каждого батча — smoke-импорт
и/или тесты.

- **Батч 1 — `configs/`**: `constants.py` (39 модульных констант + 3 функции),
  `translations.py` (`ClassVar[str]` для `TEXTS`, тип `TRANSLATIONS`).
- **Батч 2 — `src/utils/`**: `utils.py`, `AppState.py`, `LinkableValue/*`.
- **Батч 3 — `src/editions/` + инфраструктура `src/gtnh/`**: `base.py`,
  `vanilla.py`, `editions/__init__.py`, `gtnh/__init__.py`, `constants.py`,
  `controls.py`, `aspect.py`.
- **Батч 4 — `src/UI/`**: `primitives/*` (`Object`, `Text`, `Point`, `Rect`,
  `Line`, `Circle`, `Image`, `values`), затем `OverlayUI.py`.
- **Батч 5 — `src/controllers/`**: `Aspect.py`, `Point.py`, `ThaumInteractor.py`.
- **Батч 6 — `src/controllers/Scenarios/`**: `shared.py`, `__init__.py`,
  `scenario00`–`scenario8`.
- **Батч 7 — `src/logic/`**: `LinksGeneration.py`, `digit_recognition.py`,
  `Neurolink.py`, `onnx_inference/*`.
- **Батч 8 — логика `src/gtnh/`**: `interactor.py`, `recognition.py`,
  `mixing.py`, `scenarios/*`.
- **Батч 9 — `src/main.py`**: модульные переменные, `parseArgs`, `main`.

## 7. Верификация

1. **AST-самопроверка** отсутствия пропусков по `src/` + `configs/`
   (скрипт — Приложение A). Ожидание: 0 пропущенных параметров, 0 пропущенных
   возвратов, 0 неаннотированных class/module-переменных, кроме членов `Enum`.
2. **Smoke-импорт** + проверки отсутствия изменения поведения:
   - `configs.translations`: `TEXTS.languageName == "languageName"`,
     `TEXTS.Buttons` не стал набором полей dataclass;
   - `configs.constants`: значения `MARGIN == 20`, `DELAY_BETWEEN_EVENTS == 0.15`;
   - `src/UI/OverlayUI.py`: `KeyboardKeys.esc.value == 1`, число членов не
     изменилось;
   - создать `Aspect(...)`, `P(0.0, 0.0)`; импорт `utils.AppState` не падает.
3. **Существующие тесты**: `python -m unittest discover tests` (при наличии
   установленных зависимостей).
4. **`ruff check src configs`** — без новых предупреждений.
5. **Ревью `git diff`**: изменения — только аннотации, логика не затронута.

## 8. Риски и границы

- Внешние пакеты без стабов → местами `Any`, типизация неполная; это осознанный
  компромисс. Ложных ошибок не будет, т.к. тип-чекер не подключается.
- Главный риск — изменить рантайм-поведение аннотацией: dataclass
  (§5.1) и `Enum` (§5.2). Эти места проверяются smoke-тестами.
- Mutable default-аргументы (`args=[]`, `kwargs={}`) — существующая проблема,
  в рамках задачи **не исправляется**.
- Объём — ~309 функций / 73 атрибута / 66 модульных переменных; разбит на
  9 батчей для поэтапного ревью.

## 9. Критерии готовности

- AST-самопроверка (Приложение A) выдаёт 0 пропусков для `src/` + `configs/`.
- `ruff check` чист.
- Существующие тесты проходят; smoke-проверки §7.2 успешны.
- `git diff` не содержит изменений логики.

## Приложение A. Скрипт AST-самопроверки

Запускается как `python <script>.py` из корня репозитория; ничего не меняет.

```python
import ast, os

ROOTS = ["src", "configs"]
EXCLUDE_ARGS = {"self", "cls"}


def is_enum_class(node: ast.ClassDef) -> bool:
    return any("Enum" in ast.unparse(base) for base in node.bases)


def collect(tree):
    enum_classes = {
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and is_enum_class(n)
    }
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            named = args.posonlyargs + args.args + args.kwonlyargs
            if args.vararg:
                named.append(args.vararg)
            if args.kwarg:
                named.append(args.kwarg)
            missing = [
                a.arg for a in named
                if a.arg not in EXCLUDE_ARGS and a.annotation is None
            ]
            if missing or node.returns is None:
                hits.append((node.lineno, "func", node.name, missing,
                             node.returns is None))
        elif isinstance(node, ast.ClassDef) and node.name not in enum_classes:
            for st in node.body:
                if isinstance(st, ast.Assign):
                    for tg in st.targets:
                        if isinstance(tg, ast.Name):
                            hits.append((st.lineno, "class-attr", tg.id, [], False))
    for st in tree.body:
        if isinstance(st, ast.Assign):
            for tg in st.targets:
                if isinstance(tg, ast.Name):
                    hits.append((st.lineno, "module-var", tg.id, [], False))
    return hits


def main():
    total = 0
    for root in ROOTS:
        for dirpath, _, filenames in os.walk(root):
            if "__pycache__" in dirpath:
                continue
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                tree = ast.parse(open(path, encoding="utf-8").read())
                hits = collect(tree)
                if hits:
                    total += len(hits)
                    print(f"{path}: {len(hits)}")
                    for line, kind, ident, missing, ret in hits:
                        detail = f" args={missing}" if missing else ""
                        detail += " return" if ret else ""
                        print(f"    {line}: {kind} {ident}{detail}")
    print(f"TOTAL MISSING: {total}")


if __name__ == "__main__":
    main()
```
