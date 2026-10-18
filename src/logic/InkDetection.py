from configs.constants import INK_EXHAUSTED_MARKER_CELLS

HexagonsCells = set[tuple[int, int]]


def isInkExhaustedByField(noneHexagons: HexagonsCells,
                          markerCells: HexagonsCells = INK_EXHAUSTED_MARKER_CELLS) -> bool:
    """Определяет исчерпание чернильницы по данным определения поля.

    Когда в чернильнице кончаются чернила, игра перестаёт ставить аспекты и перекрывает
    часть клеток поля: эти клетки больше не определяются ни как аспект, ни как свободный
    шестиугольник, то есть попадают в noneHexagons.

    Пустой набор маркерных клеток (значение по умолчанию в configs/constants.py) полностью
    выключает отслеживание. Достаточно одной маркерной клетки в noneHexagons.
    """
    return bool(markerCells) and any(cell in noneHexagons for cell in markerCells)


def markerCellsBecameNone(markerCells: HexagonsCells, knownCellsBefore: HexagonsCells,
                          noneHexagons: HexagonsCells) -> bool:
    """Определяет исчерпание чернильницы по изменению маркерных клеток во время выкладывания.

    knownCellsBefore — клетки, которые до начала выкладывания были свободными (freeHexagons)
    или занятыми аспектами (existingAspects). Если хотя бы одна маркерная клетка из них
    вдруг стала none, значит выкладывание перестало работать (чернила кончились), и его надо
    прервать, а не доводить до конца вслепую.

    Пустой набор маркерных клеток выключает отслеживание.
    """
    return bool(markerCells) and any(cell in knownCellsBefore and cell in noneHexagons
                                     for cell in markerCells)