from configs.constants import (INK_EXHAUSTED_MARKER_CELLS, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT,
                               INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE, INK_EXHAUSTED_MIN_FREE_OUTSIDE_BAND)

HexagonsCells = set[tuple[int, int]]


def undetectedHexagons(noneHexagons: HexagonsCells, aspectCells: HexagonsCells) -> HexagonsCells:
    """Клетки, которые не опознаны ни как свободный шестиугольник, ни как аспект.

    `noneHexagons` из определения поля (`ThaumInteractor.getExistingAspectsOnField`) содержит
    ещё и клетки с распознанными аспектами: аспект в клетке — это норма, поэтому из
    "пропавших" клеток его надо исключить.
    """
    return set(noneHexagons) - set(aspectCells)


class FieldMarkers:
    """Состояние маркерных клеток поля.

    present — маркерные клетки, которые вообще есть на этом поле,
    lost — из них те, что не опознаны ни как свободный шестиугольник, ни как аспект,
    visibleAspects — из них те, где стоит распознанный аспект: его иконка видна даже под
    плашкой "You have run out of ink!", поэтому потеря в такой клетке не наблюдаема,
    freeOutsideBand — сколько свободных шестиугольников опознано вне полосы: у решённого
    или пустого поля их нет вовсе, а при исчерпании чернил поле вокруг полосы остаётся.
    """

    def __init__(self, present: HexagonsCells, lost: HexagonsCells,
                 visibleAspects: HexagonsCells = set(), freeOutsideBand: int = 0) -> None:
        self.present = set(present)
        self.lost = set(lost)
        self.visibleAspects = set(visibleAspects)
        self.freeOutsideBand = freeOutsideBand

    @property
    def observable(self) -> HexagonsCells:
        """Клетки, в которых потеря клетки вообще была бы видна."""
        return self.present - self.visibleAspects

    @property
    def lostShare(self) -> float:
        """Доля пропавших маркерных клеток от наблюдаемых маркерных клеток поля."""
        return len(self.lost) / len(self.observable) if self.observable else 0.0

    def __repr__(self) -> str:
        return (f"FieldMarkers(lost {len(self.lost)} of {len(self.observable)} observable "
                f"({len(self.present)} on field), free outside band {self.freeOutsideBand} "
                f"= {self.lostShare:.0%})")


def collectFieldMarkers(aspectCells: HexagonsCells, freeHexagons: HexagonsCells,
                        noneHexagons: HexagonsCells,
                        markerCells: HexagonsCells = INK_EXHAUSTED_MARKER_CELLS) -> FieldMarkers:
    """Собирает состояние маркерных клеток по результату определения поля."""
    return FieldMarkers(
        present=set(markerCells) & (set(noneHexagons) | set(freeHexagons)),
        lost=set(markerCells) & undetectedHexagons(noneHexagons, aspectCells),
        visibleAspects=set(markerCells) & set(aspectCells),
        freeOutsideBand=len(set(freeHexagons) - set(markerCells)),
    )


def isInkExhausted(markers: FieldMarkers,
                   minCount: int = INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT,
                   minShare: float = INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE,
                   minFreeOutsideBand: int = INK_EXHAUSTED_MIN_FREE_OUTSIDE_BAND) -> bool:
    """Определяет исчерпание чернильницы по маркерным клеткам поля.

    Когда в чернильнице кончаются чернила, игра перестаёт ставить аспекты и пишет
    "You have run out of ink!" плашкой в середине поля: вся полоса маркерных клеток
    перестаёт определяться как свободные шестиугольники, то есть пропадает почти целиком.

    Требуем и долю пропавших клеток, и минимальное их количество: единичные потери клеток
    бывают и в нормальном поле (промахи определения, аспекты, которых бот не знает), а при
    исчерпании пропадает вся полоса. Плюс требуем, чтобы вне полосы ещё определялись
    свободные шестиугольники: у решённого исследования поле пустое, и полоса в нём
    "пропадает" так же, как при исчерпании, но это не исчерпание.

    Пустой набор маркерных клеток выключает отслеживание.
    """
    return (markers.freeOutsideBand >= minFreeOutsideBand
            and len(markers.lost) >= minCount
            and markers.lostShare >= minShare)


def markersLostSince(knownCellsBefore: HexagonsCells, markers: FieldMarkers) -> FieldMarkers:
    """Оставляет только те пропавшие маркерные клетки, которые до выкладывания были на месте.

    `knownCellsBefore` — клетки, которые до начала выкладывания были свободными (freeHexagons)
    или занятыми аспектами (existingAspects). Если маркерные клетки из них вдруг перестали
    определяться, значит игра больше не принимает аспекты (чернила кончились), и выкладывание
    надо прервать, а не доводить до конца вслепую.
    """
    return FieldMarkers(present=markers.present, lost=markers.lost & set(knownCellsBefore),
                        visibleAspects=markers.visibleAspects,
                        freeOutsideBand=markers.freeOutsideBand)