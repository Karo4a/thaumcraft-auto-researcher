from controllers.Aspect import Aspect


class GtnhAspect(Aspect):
    rectAspectsNumber: int | None

    def __init__(self, name: str, idx: int, cellX: int = None, cellY: int = None, rectAspectsNumber: int = None):
        super().__init__(name, idx, cellX, cellY)
        self.rectAspectsNumber = rectAspectsNumber
