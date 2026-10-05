from editions.base import BaseEdition


class VanillaEdition(BaseEdition):
    id = "vanilla"
    displayName = "Thaumcraft"


def createEdition() -> BaseEdition:
    return VanillaEdition()
