from typing import Callable


class BaseEdition:
    id: str = "vanilla"
    displayName: str = "Thaumcraft"

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
