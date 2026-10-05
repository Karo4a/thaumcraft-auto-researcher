import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from editions.base import BaseEdition

_EDITION_MODULES: dict[str, str] = {
    "vanilla": "editions.vanilla",
    "gtnh": "gtnh",
}

_currentEdition: "BaseEdition | None" = None


def getEditionNames() -> list[str]:
    return list(_EDITION_MODULES.keys())


def getEditionDisplayName(name: str) -> str:
    module = importlib.import_module(_EDITION_MODULES[name])
    return module.createEdition().displayName


def selectEdition(name: str) -> "BaseEdition":
    global _currentEdition
    if name not in _EDITION_MODULES:
        raise ValueError(f"Unknown edition: {name}")
    module = importlib.import_module(_EDITION_MODULES[name])
    _currentEdition = module.createEdition()
    logging.info(f"Edition selected: {name}")
    return _currentEdition


def getEdition() -> "BaseEdition":
    global _currentEdition
    if _currentEdition is None:
        selectEdition("vanilla")
    return _currentEdition
