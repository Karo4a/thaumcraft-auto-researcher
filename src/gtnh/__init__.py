import json
import os
import sys

from editions.base import BaseEdition
from gtnh.constants import DELAY_BETWEEN_EVENTS as GTNH_DELAY_BETWEEN_EVENTS, \
    DELAY_BETWEEN_RENDER as GTNH_DELAY_BETWEEN_RENDER


def _dataPath(relativePath: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'gtnh', 'data', relativePath)


def _loadJson(relativePath: str) -> dict:
    with open(_dataPath(relativePath), 'r', encoding='utf-8') as file:
        return json.load(file)


class GtnhEdition(BaseEdition):
    id = "gtnh"
    displayName = "GTNH"
    delayBetweenEvents = GTNH_DELAY_BETWEEN_EVENTS
    delayBetweenRender = GTNH_DELAY_BETWEEN_RENDER

    @property
    def scenarioOverrides(self) -> dict:
        from gtnh.scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
        from gtnh.scenarios.scenario4_ChooseThaumVersion import chooseThaumVersion as gtnhChooseThaumVersion
        from gtnh.scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
        return {
            "confirmThaumWindowSlots": confirmThaumWindowSlots,
            "chooseThaumVersion": gtnhChooseThaumVersion,
            "detectionAspectsDialogue": detectionAspectsDialogue,
        }

    def validVersionKeys(self) -> set[str] | None:
        return {"GTNH"}

    def createTI(self, UI, noPointsConfigCallback, noSelectedVersionCallback):
        from controllers.ThaumInteractor import _createTIDefault
        from gtnh.interactor import GtnhThaumInteractor
        return _createTIDefault(UI, noPointsConfigCallback, noSelectedVersionCallback,
                                interactorClass=GtnhThaumInteractor)

    def readThaumWindowControls(self) -> dict | None:
        from gtnh.controls import readGtnhThaumWindowControls
        return readGtnhThaumWindowControls()

    def saveThaumWindowControls(self, *args, **kwargs):
        from gtnh.controls import saveGtnhThaumWindowControls
        from utils import AppState
        saveGtnhThaumWindowControls(*args, **kwargs)
        AppState.rereadThaumWindowControls()

    def extraAspectRecipes(self) -> dict:
        return _loadJson(os.path.join('aspects_configs', 'gtnhAspectsRecipes.json'))

    def extraAddonsRecipes(self) -> dict:
        return _loadJson(os.path.join('aspects_configs', 'gtnhAddonsAspectsRecipes.json'))


def createEdition():
    return GtnhEdition()


def getGtnhVersions() -> list[str]:
    return list(createEdition().extraAspectRecipes().keys())
