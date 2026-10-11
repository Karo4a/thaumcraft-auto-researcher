import logging

_research: int = 0
_solve: int = 0


def setResearch(idx: int) -> None:
    global _research
    _research = idx


def setSolve(idx: int) -> None:
    global _solve
    _solve = idx


def incrementResearch() -> None:
    global _research
    _research += 1


def incrementSolve() -> None:
    global _solve
    _solve += 1


def resetSolve() -> None:
    global _solve
    _solve = 0


def currentContext() -> str:
    if _research == 0 and _solve == 0:
        return "-"
    return f"R{_research} S{_solve}"


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.solutionContext = currentContext()
        return True
