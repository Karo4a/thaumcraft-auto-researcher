import logging

from PyQt5.QtGui import QColor

from UI.OverlayUI import OverlayUI
from UI.primitives import Text
from configs.translations import TEXTS
from controllers import Scenarios
from controllers.Scenarios.shared import PointTextAnchor, createNextBackButtonsAndText
from configs.constants import MARGIN
from utils import AppState

DEFAULT_CHOOSE_EDITION_TEXT = "Select game edition / Выберите режим игры:"


def chooseEdition(UI: OverlayUI):
    import editions

    UI.clearAll()
    UI.createExitButton()

    def onSubmit():
        if selectedEdition[0] is None:
            logging.warning("Trying to go next but edition is not selected")
            return
        logging.info(f"Selected edition: {selectedEdition[0]}")
        AppState.saveEdition(selectedEdition[0])
        Scenarios.activateEdition(selectedEdition[0])
        Scenarios.routeStartup(UI)

    (infoText, nextButton, _) = createNextBackButtonsAndText(
        UI,
        AppState.translatedTexts.get(TEXTS.chooseEdition, DEFAULT_CHOOSE_EDITION_TEXT),
        onSubmit, [],
        None, [],
        "Go next >",
        None,
    )

    editionNames = editions.getEditionNames()
    editionDisplayNames = list(map(editions.getEditionDisplayName, editionNames))
    editionTextObjects = []

    selectedEditionObject: list[Text | None] = [None]
    selectedEdition: list[str | None] = [None]

    oldEditionKey = AppState.selectedEdition
    if oldEditionKey is None:
        oldEditionKey = "gtnh" if "gtnh" in editionNames else editionNames[0]
        logging.info(f"Selected edition in config is none. Selecting default: {oldEditionKey}")
    else:
        logging.info(f"Selected in config edition is: {oldEditionKey}")

    oldInfoTextCallback = infoText.onMoveCallback

    def updateTextsPosition():
        oldInfoTextCallback()
        startCurY = nextButton.y + nextButton.h + MARGIN * 2
        curY = startCurY
        curX = PointTextAnchor.x
        for i in range(len(editionTextObjects)):
            textObject = editionTextObjects[i]
            if curY > UI.height() - textObject.h:
                curX += 300
                curY = startCurY
            textObject.y = curY
            textObject.x = curX
            curY += textObject.h + MARGIN

    infoText.LT.onMoveCallback = updateTextsPosition
    infoText.onMoveCallback = updateTextsPosition
    startCurY = nextButton.y + nextButton.h + MARGIN * 2
    curY = startCurY
    curX = PointTextAnchor.x
    for i in range(len(editionNames)):
        editionKey = editionNames[i]
        editionName = editionDisplayNames[i]

        def onClickEdition(editionObject, editionKey):
            logging.debug(f"Click on edition {editionKey}")
            selectEdition(editionObject, editionKey)

        def selectEdition(editionObject, editionKey):
            if selectedEditionObject[0] is not None:
                selectedEditionObject[0].setColor(QColor('white'))
            logging.debug(f"Edition {editionKey} selected in UI. Previous selected edition is {selectedEdition[0]}")
            selectedEdition[0] = editionKey
            selectedEditionObject[0] = editionObject
            selectedEditionObject[0].setColor(QColor('purple'))

        editionObject = UI.addObject(Text(
            0, 0,
            editionName,
            color=QColor('white'),
            withBackground=True,
            padding=MARGIN,
            UI=UI,
            onClickCallback=onClickEdition,
            hoverable=True,
        ))
        if curY > UI.height() - editionObject.h:
            curX += 300
            curY = startCurY
        editionObject.x = curX
        editionObject.y = curY
        curY += editionObject.h + MARGIN
        editionObject.onClickCallbackArgs = [editionObject, editionKey]
        editionTextObjects.append(editionObject)
        if oldEditionKey == editionKey:
            selectEdition(editionObject, editionKey)

    logging.info(f"Selecting edition dialogue showed. Editions: {editionNames}")
