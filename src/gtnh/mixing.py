"""
Семантически точный порт оптимизированного mixAspect из GTNH-ветки master (коммит 6eb36de).
Известные особенности (сохраняются осознанно для parity):
- общий базовый аспект, встречающийся в нескольких рецептах, может быть недосчитан,
  и план окажется невыполнимым при нехватке запаса (вызывающий код обязан проверять counts при исполнении);
- рецепты раскрываются даже при mixingTimes <= 0, поэтому возможен None там, где микс фактически возможен;
- planMixing мутирует count аспектов (None -> 0).
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional


def planMixing(aspect: Any, targetCount: int,
               getAspectByName: Callable[[str], Any],
               getAspectRecipeByName: Callable[[str], list[str]]) -> Optional[list[tuple[Any, int]]]:
    """
    Строит план микса аспекта до targetCount снизу вверх (ингредиенты раньше результата).
    Возвращает список пар (аспект, количество миксов) или None, если микс невозможен.
    Повторяет алгоритм GTNH-ветки master.
    """
    if not aspect.count:
        aspect.count = 0
    if aspect.count >= targetCount:
        return None
    mixingTimes = targetCount - aspect.count
    logging.info(f"Planning mixing aspect {aspect} to {targetCount} for {mixingTimes} times...")
    recipe = getAspectRecipeByName(aspect.name)
    if len(recipe) < 2:  # Aspect is basic (Aqua, Terra, Aer, Ordo, Perditio)
        if aspect.count < mixingTimes:
            logging.critical(f"Ran out of basic aspect {aspect.name}")
        return None

    mixingStack = [aspect]
    totalMixingForAspect = {aspect.name: mixingTimes}
    totalCostBasicAspects = {}
    notProcessedRecipes = [recipe]

    while notProcessedRecipes:
        currentRecipe = notProcessedRecipes.pop()
        for aspectInRecipe in map(getAspectByName, currentRecipe):
            nextRecipe = getAspectRecipeByName(aspectInRecipe.name)
            if not aspectInRecipe.count:
                aspectInRecipe.count = 0
            mixingTimes = targetCount - aspectInRecipe.count
            if len(nextRecipe):  # Not basic aspect
                notProcessedRecipes.append(nextRecipe)
                mixingStack.append(aspectInRecipe)
                totalMixingForAspect[aspectInRecipe.name] = \
                    totalMixingForAspect.get(aspectInRecipe.name, 0) + mixingTimes
            else:
                totalCostBasicAspects[aspectInRecipe.name] = \
                    totalCostBasicAspects.get(aspectInRecipe.name, 0) + mixingTimes
                if totalCostBasicAspects[aspectInRecipe.name] > aspectInRecipe.count:
                    return None

    plan = []
    while mixingStack:
        aspectRecipe = mixingStack.pop()
        times = totalMixingForAspect[aspectRecipe.name]
        totalMixingForAspect[aspectRecipe.name] = 0
        if times > 0:
            plan.append((aspectRecipe, times))
    return plan
