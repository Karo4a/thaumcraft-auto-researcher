from typing import Callable

from configs.constants import DELAY_BETWEEN_EVENTS, DELAY_BETWEEN_RENDER


class BaseEdition:
    id: str = "vanilla"
    displayName: str = "Thaumcraft"
    delayBetweenEvents: float = DELAY_BETWEEN_EVENTS
    delayBetweenRender: float = DELAY_BETWEEN_RENDER

    @property
    def scenarioOverrides(self) -> dict[str, Callable]:
        return {}

    def validVersionKeys(self) -> set[str] | None:
        """None means 'no extra restriction' (validate against the loaded recipe map)."""
        return None

    def createTI(self, UI, noPointsConfigCallback, noSelectedVersionCallback):
        from controllers.ThaumInteractor import _createTIDefault
        return _createTIDefault(UI, noPointsConfigCallback, noSelectedVersionCallback)

    def readThaumWindowControls(self) -> dict | None:
        from configs.constants import THAUM_CONTROLS_CONFIG_PATH
        from utils.AppState import readJSONConfig
        return readJSONConfig(THAUM_CONTROLS_CONFIG_PATH)

    def saveThaumWindowControls(self, *args, **kwargs):
        from utils import AppState
        AppState._saveVanillaThaumWindowControls(*args, **kwargs)

    def extraAspectRecipes(self) -> dict:
        return {}

    def extraAddonsRecipes(self) -> dict:
        return {}

    def includeBaseAddonRecipes(self) -> bool:
        """Whether the shared addons recipe file applies to this edition."""
        return True
