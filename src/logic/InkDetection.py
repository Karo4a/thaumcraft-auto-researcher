from configs.constants import INK_EXHAUSTED_MARKER_CELLS, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT

HexagonsCells = set[tuple[int, int]]


def undetectedHexagons(noneHexagons: HexagonsCells, aspectCells: HexagonsCells) -> HexagonsCells:
    """Клетки, которые не опознаны ни как свободный шестиугольник, ни как аспект.

    `noneHexagons` из определения поля (`ThaumInteractor.getExistingAspectsOnField`) содержит
    ещё и клетки с распознанными аспектами: аспект в клетке — это норма, поэтому из
    "пропавших" клеток его надо исключить.
    """
    return set(noneHexagons) - set(aspectCells)


def isInkExhaustedByField(undetected: HexagonsCells,
                          markerCells: HexagonsCells = INK_EXHAUSTED_MARKER_CELLS,
                          minMarkerCells: int = INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT) -> bool:
    """Определяет исчерпание чернильницы по данным определения поля.

    Когда в чернильнице кончаются чернила, игра перестаёт ставить аспекты и пишет
    "You have run out of ink!" плашкой в середине поля: маркерные клетки поля (полоса
    в середине) перестают определяться как свободные шестиугольники.

    Пустой набор маркерных клеток выключает отслеживание (всегда False).
    """
    if not markerCells:
        return False
    undetectedMarkers = sum(1 for cell in markerCells if cell in undetected)
    return undetectedMarkers >= minMarkerCells


def markerCellsBecameUndetected(markerCells: HexagonsCells, knownCellsBefore: HexagonsCells,
                                undetected: HexagonsCells,
                                minMarkerCells: int = INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT) -> bool:
    """Определяет исчерпание чернильницы по изменению маркерных клеток во время выкладывания.

    `knownCellsBefore` — клетки, которые до начала выкладывания были свободными (freeHexagons)
    или занятыми аспектами (existingAspects). Если маркерные клетки из них вдруг перестали
    определяться, значит игра больше не принимает аспекты (чернила кончились), и выкладывание
    надо прервать, а не доводить до конца вслепую.

    Пустой набор маркерных клеток выключает отслеживание.
    """
    if not markerCells:
        return False
    becameUndetected = sum(1 for cell in markerCells if cell in knownCellsBefore and cell in undetected)
    return becameUndetected >= minMarkerCells