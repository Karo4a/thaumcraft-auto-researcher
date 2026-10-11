from editions.base import BaseEdition


class VanillaEdition(BaseEdition):
    id: str = "vanilla"
    displayName: str = "Thaumcraft"


def createEdition() -> BaseEdition:
    return VanillaEdition()
