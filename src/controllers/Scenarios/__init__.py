from controllers.Scenarios.scenario00_Edition import chooseEdition
from controllers.Scenarios.scenario0_Language import chooseLanguage
from controllers.Scenarios.scenario1_Enroll import enroll
from controllers.Scenarios.scenario2_ConfigureThaumWindow import configureThaumWindowCoords
from controllers.Scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
from controllers.Scenarios.scenario4_ChooseThaumVersion import chooseThaumVersion
from controllers.Scenarios.scenario5_BeReadyForStartSolving import beReadyForStartSolving
from controllers.Scenarios.scenario6_DetectAspectsCreateTI import beReadyForCreatingTI
from controllers.Scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
from controllers.Scenarios.scenario8_Researchings import runResearching
from utils import AppState

# Снимок дефолтных реализаций ДО любых подмен (важно: getattr на момент импорта)
_DEFAULT_SCENARIOS = {
    "confirmThaumWindowSlots": confirmThaumWindowSlots,
    "chooseThaumVersion": chooseThaumVersion,
    "detectionAspectsDialogue": detectionAspectsDialogue,
}


def applyEdition(edition):
    unknownScenarioNames = set(edition.scenarioOverrides) - set(_DEFAULT_SCENARIOS)
    if unknownScenarioNames:
        raise ValueError(f"Edition {edition.id} overrides unknown scenarios: {sorted(unknownScenarioNames)}")
    for scenarioName, scenarioFunction in _DEFAULT_SCENARIOS.items():
        globals()[scenarioName] = scenarioFunction
    for scenarioName, scenarioFunction in edition.scenarioOverrides.items():
        globals()[scenarioName] = scenarioFunction


def activateEdition(editionName: str):
    from editions import selectEdition
    edition = selectEdition(editionName)
    applyEdition(edition)
    AppState.rereadAllConfigs()
    return edition


def routeStartup(UI):
    if AppState.selectedLanguage is None:
        chooseLanguage(UI)
    elif AppState.thaumWindowControls is None:
        configureThaumWindowCoords(UI)
    elif AppState.selectedThaumVersion is None:
        chooseThaumVersion(UI)
    else:
        beReadyForCreatingTI(UI)
