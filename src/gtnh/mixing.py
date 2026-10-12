"""
Планирование микса аспектов (GTNH).

`planMixing` строит план снизу вверх (ингредиенты раньше результата) и гарантирует его
выполнимость: на каждом шаге ингредиентов хватает с учётом запаса и того, что дадут
предыдущие шаги плана. Если микс невозможен (не хватает базовых аспектов), возвращается None,
поэтому исполняющий код (GtnhThaumInteractor.mixAspect) может доверять плану.

Особенности:
- count аспектов нормализуется (None -> 0): исполнитель уменьшает counts при взятии и миксе;
- повторяющиеся ингредиенты в рецепте (например a + a) учитываются поэлементно;
- план отсортирован по «глубине» аспекта, поэтому ингредиент всегда миксется раньше потребителя.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from controllers.Aspect import Aspect

# Защита от зацикленных рецептов: расчёт потребности монотонно растёт и в этом случае не сойдётся.
MAX_PLAN_ITERATIONS = 100


def planMixing(aspect: Aspect, targetCount: int,
               getAspectByName: Callable[[str], Aspect],
               getAspectRecipeByName: Callable[[str], list[str]]) -> list[tuple[Aspect, int]] | None:
    """
    Строит план микса аспекта до targetCount снизу вверх (ингредиенты раньше результата).
    Возвращает список пар (аспект, количество миксов) или None, если микс невозможен
    (не хватает базовых аспектов, битые рецепты) либо не нужен (аспекта уже достаточно).
    """
    if not aspect.count:
        aspect.count = 0
    if aspect.count >= targetCount:
        return None

    counts: dict[str, int] = {aspect.name: aspect.count}
    recipes: dict[str, list[str]] = {}

    def getRecipe(name: str) -> list[str]:
        if name not in recipes:
            recipes[name] = getAspectRecipeByName(name)
        return recipes[name]

    def getCount(name: str) -> int:
        if name not in counts:
            aspectByName = getAspectByName(name)
            if not aspectByName.count:
                aspectByName.count = 0
            counts[name] = aspectByName.count
        return counts[name]

    # required[X] — сколько копий X нужно получить суммарно (запас + миксы),
    # mixes[X] — сколько X надо смешать. Считаем наименьшую неподвижную точку:
    # mixes[X] = max(0, required[X] - stock[X]), а required ингредиентов = сумма миксов потребителей.
    required: dict[str, int] = {aspect.name: targetCount}
    mixes: dict[str, int] = {}

    for _ in range(MAX_PLAN_ITERATIONS):
        newMixes = {name: max(0, need - getCount(name)) for name, need in required.items()}
        if newMixes == mixes:
            break
        mixes = newMixes
        required = {aspect.name: targetCount}
        for name, timesMixing in mixes.items():
            if timesMixing <= 0:
                continue
            for ingredientName in getRecipe(name):
                required[ingredientName] = required.get(ingredientName, 0) + timesMixing
    else:
        logging.critical(f"Cannot plan mixing {aspect.name}: aspect recipes are cyclic")
        return None

    for name, timesMixing in mixes.items():
        if timesMixing > 0 and len(getRecipe(name)) < 2:  # Aspect is basic (Aqua, Terra, Aer, Ordo, Perditio)
            logging.critical(f"Ran out of basic aspect {name}")
            return None

    depthCache: dict[str, int] = {}

    def getDepth(name: str, seen: frozenset[str] = frozenset()) -> int:
        if name in depthCache:
            return depthCache[name]
        recipe = getRecipe(name)
        if not recipe or name in seen:
            return 0
        depth = 1 + max(getDepth(ingredient, seen | {name}) for ingredient in recipe)
        depthCache[name] = depth
        return depth

    plan: list[tuple[Aspect, int]] = [
        (getAspectByName(name), timesMixing)
        for name, timesMixing in mixes.items() if timesMixing > 0
    ]
    plan.sort(key=lambda item: (getDepth(item[0].name), item[0].name))
    logging.info(f"Plan of mixing {aspect.name} to {targetCount}: {plan}")
    return plan


def selectCraftableAspects(allAspectNames: list[str], recipes: dict[str, list[str]],
                           availableNames: set[str]) -> list[str]:
    """
    Возвращает имена аспектов (в порядке allAspectNames), которые сейчас можно скрафтить:
    аспект ещё не открыт, у него есть рецепт, и оба ингредиента уже доступны.
    """
    craftable: list[str] = []
    for name in allAspectNames:
        if name in availableNames:
            continue
        recipe = recipes.get(name)
        if recipe and set(recipe).issubset(availableNames):
            craftable.append(name)
    return craftable
