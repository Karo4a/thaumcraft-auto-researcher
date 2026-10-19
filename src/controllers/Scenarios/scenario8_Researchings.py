import logging
import math
import threading

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

from utils import AppState
from UI.OverlayUI import KeyboardKeys, OverlayUI
from UI.primitives import Image, Circle, UIPrimitive
from UI.primitives.Text import Text
from configs.translations import TEXTS
from controllers.Aspect import Aspect
from controllers.ThaumInteractor import ThaumInteractor
from controllers import Scenarios
from controllers.Scenarios.shared import createButtonsAndText, createNotification, NOTIFICATION_BACKGROUND_ERROR, \
    NotificationManager
from logic.LinksGeneration import generateLinkMap
from logic.InkDetection import collectFieldMarkers, isInkExhausted, markersLostSince
from configs.constants import MARGIN, LINK_GENERATION_MAX_TIME_MS, MAX_SOLVE_RETRIES, THAUM_HEXAGONS_SLOTS_COUNT, \
    DONATE_URL_RUSSIA, DONATE_CRYPTO_ID_GLOBAL, INK_EXHAUSTED_MARKER_CELLS, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT, \
    INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE, INK_CHECK_EVERY_N_PLACED_ASPECTS
from utils.utils import renderDelay, eventsDelay


def runResearching(UI: OverlayUI, TI: ThaumInteractor) -> None:
    logging.info(f"Run researching scenario started")
    UI.clearAll()
    exitButtonObject = UI.createExitButton()

    class Cell:
        x: int | None = None
        y: int | None = None
        object: Circle | None = None
        imageObject: Image | None = None
        aspect: Aspect | None = None
        isNone: bool = False

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

        def __repr__(self) -> str:
            return f"Cell([{self.x}, {self.y}], aspect={self.aspect}, isNone={self.isNone})"

    cells: list[Cell] = []
    selectedCell: list[Cell | None, QColor | None] = [None, None]  # list to make it mutable
    currentLinkMap: list[dict[tuple[int, int], str]] = [{}]  # list to make it mutable

    cellColorFree = QColor('white')
    cellColorNone = QColor('black')
    cellColorAspect = QColor('antiquewhite')
    cellColorFree.setAlpha(20)
    cellColorNone.setAlpha(150)
    cellColorAspect.setAlpha(200)

    # it all Lists to make them mutable
    existingAspects = [{}]
    freeHexagons = [set()]
    noneHexagons = [set()]
    multyResearchesCountLeft = [0]
    inkExhausted = [False]
    cellsKnownBeforePlacing = [set()]

    cellsObjects: list[Image | Circle] = []

    # --- Cells dialogue elements
    cellSettingsStateDialogueObjects: list[UIPrimitive] = []

    def updateDetectingField() -> None:
        logging.debug(f'Run detecting aspects on field')
        UI.safeSetAllObjectsVisibility(False)
        UI.safeSetObjectsVisibility([exitButtonObject], True)
        UI.safeRepaint()
        renderDelay()
        (existingAspects[0], noneHexagons[0], freeHexagons[0]) = TI.getExistingAspectsOnField()
        markers = collectFieldMarkers(set(existingAspects[0]), freeHexagons[0], noneHexagons[0],
                                      INK_EXHAUSTED_MARKER_CELLS)
        inkExhausted[0] = isInkExhausted(markers, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT,
                                         INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE)
        logging.debug(f"Field markers: {markers!r} -> ink exhausted: {inkExhausted[0]}")
        if inkExhausted[0]:
            logging.critical("Ink exhausted: marker cells of the field are not detected")
        logging.debug(f'Aspects on field detected')

    def updateSolving(interruptingFlag: list[bool] = [False]) -> None:
        logging.debug(f'Starts updating solve...')

        if inkExhausted[0]:
            # Чернила кончились: выкладывание отключено, решение не генерируем,
            # показываем поле таким, каким его увидело определение
            logging.critical("Ink exhausted: solving is disabled")
            currentLinkMap[0] = existingAspects[0]
            updateCellsImage()
            return

        # Start solving
        solving = None
        solveRetries = 0
        logging.debug(f'Trying to generate solving, try number: {solveRetries + 1}')
        while solveRetries < MAX_SOLVE_RETRIES and solving is None:
            solving = generateLinkMap(
                existingAspects[0],
                noneHexagons[0],
                TI.getAvailableAspectsNames(),
                interruptingFlag
            )
            solveRetries += 1

        if solving is None:
            currentLinkMap[0] = existingAspects[0]
            logging.debug(f'None solving gotten from "generateLinkMap"')
        else:
            currentLinkMap[0] = solving
            logging.debug(f'New solving generated {currentLinkMap[0]}')
        # Rerender cells images
        updateCellsImage()

    def updateCellsImage() -> None:
        # Fill cells by gotten solve
        aspectsCoords = currentLinkMap[0].keys()
        for cell in cells:
            cell.isNone = True
            cell.aspect = None
            cell.imageObject.clearImage()
            # is aspect:
            for coords in aspectsCoords:
                if (cell.x == coords[0]) and (cell.y == coords[1]):
                    aspectObj = TI.getAspectByName(currentLinkMap[0][coords])
                    cell.aspect = aspectObj
                    cell.isNone = False
                    cell.object.setColor(cellColorAspect)
                    cell.imageObject.setImage(aspectObj.pixMapImage)
                    break
            # is free:
            if (cell.x, cell.y) in freeHexagons[0]:
                if cell.aspect is not None:
                    continue
                cell.isNone = False
                cell.object.setColor(cellColorFree)
            # is none:
            if cell.isNone:
                cell.object.setColor(cellColorNone)
        logging.debug(f'New images placed to all cells')

    def onClickCellIsNone() -> None:
        logging.debug(f'Click on "Cell is none". Selected cell: {selectedCell[0]}')
        if selectedCell[0] is None:
            return
        coords = (selectedCell[0].x, selectedCell[0].y)
        if existingAspects[0].get(coords) is not None: del existingAspects[0][coords]
        freeHexagons[0].discard(coords)
        noneHexagons[0].add(coords)
        selectedCell[0] = None
        updateSolving()
        switchToActiveState()

    def onClickCellIsAspect(aspect: Aspect) -> None:
        logging.debug(f'Click on "Cell is aspect {aspect}". Selected cell: {selectedCell[0]}')
        if selectedCell[0] is None:
            return
        coords = (selectedCell[0].x, selectedCell[0].y)
        existingAspects[0][coords] = aspect.name
        freeHexagons[0].discard(coords)
        noneHexagons[0].discard(coords)
        selectedCell[0] = None
        updateSolving()
        switchToActiveState()

    def onClickCellIsFree() -> None:
        logging.debug(f'Click on "Cell is free". Selected cell: {selectedCell[0]}')
        if selectedCell[0] is None:
            return
        coords = (selectedCell[0].x, selectedCell[0].y)
        if existingAspects[0].get(coords) is not None: del existingAspects[0][coords]
        freeHexagons[0].add(coords)
        noneHexagons[0].discard(coords)
        selectedCell[0] = None
        updateSolving()
        switchToActiveState()

    def startCellDialogue(cell: Cell) -> None:
        switchToCellSettingsState()
        if selectedCell[0]:
            newColor = QColor(selectedCell[0].object.color)
            newColor.setAlpha(selectedCell[1])
            selectedCell[0].object.setColor(newColor)
        selectedCell[0] = cell
        newColor = QColor(cell.object.color)
        selectedCell[1] = newColor.alpha()
        newColor.setAlpha(130)
        cell.object.setColor(newColor)
        logging.debug(f'Showed cell state selecting dialogue')

    def exitCellDialogue() -> None:
        switchToActiveState()
        if not selectedCell[0]:
            return
        newColor = QColor(selectedCell[0].object.color)
        newColor.setAlpha(selectedCell[1])
        selectedCell[0].object.setColor(newColor)
        selectedCell[0] = None
        logging.debug(f'Exit cell state selecting dialogue. Showed only cells field')

    # draw clickable cells
    for ix in range(-THAUM_HEXAGONS_SLOTS_COUNT // 2 + 1, THAUM_HEXAGONS_SLOTS_COUNT // 2 + 1):
        for iy in range(-THAUM_HEXAGONS_SLOTS_COUNT // 2 + (abs(ix) + 1) // 2 + 1,
                        THAUM_HEXAGONS_SLOTS_COUNT // 2 - (abs(ix)) // 2 + 1):
            hexagonCenterX = TI.rectHexagonsCC.x + ix * TI.hexagonSlotSizeX
            hexagonCenterY = TI.rectHexagonsCC.y + iy * TI.hexagonSlotSizeY - (ix % 2) * TI.hexagonSlotSizeY / 2
            cell = Cell(ix, iy)
            cellObject = Circle(
                hexagonCenterX,
                hexagonCenterY,
                r=TI.hexagonSlotSizeY / 2,
                color=cellColorFree,
                onClickCallback=startCellDialogue,
                onClickCallbackArgs=[cell],
                hoverable=True,
            )
            cell.object = cellObject
            imageSide = TI.hexagonSlotSizeY / math.sqrt(2)
            cellAspectImageObject = Image(
                hexagonCenterX,
                hexagonCenterY - imageSide,
                imageSide,
                imageSide,
                None
            )
            cell.imageObject = cellAspectImageObject
            cells.append(cell)
            cellsObjects.append(cellAspectImageObject)
            cellsObjects.append(cellObject)
            UI.addObject(cellObject)
            UI.addObject(cellAspectImageObject)

    # draw cell dialogue
    textYCoord = MARGIN
    textCellIsNone = UI.addObject(Text(
        MARGIN, textYCoord,
        AppState.translatedTexts[TEXTS.Buttons.setCellNotAvailable],
        color=QColor('white'),
        withBackground=True,
        backgroundOpacity=0.8,
        padding=MARGIN,
        UI=UI,
        onClickCallback=onClickCellIsNone,
        hoverable=True,
    ))
    cellSettingsStateDialogueObjects.append(textCellIsNone)
    textYCoord += textCellIsNone.h + MARGIN
    textCellIsFree = UI.addObject(Text(
        MARGIN, textYCoord,
        AppState.translatedTexts[TEXTS.Buttons.setCellFree],
        color=QColor('white'),
        withBackground=True,
        backgroundOpacity=0.8,
        padding=MARGIN,
        UI=UI,
        onClickCallback=onClickCellIsFree,
        hoverable=True,
    ))
    cellSettingsStateDialogueObjects.append(textCellIsFree)
    textYCoord += textCellIsFree.h + MARGIN * 2
    startTextYCoord = textYCoord
    textXCoord = MARGIN
    for i in range(len(TI.availableAspects)):
        aspect = TI.availableAspects[i]
        textAspect = UI.addObject(Text(
            textXCoord, textYCoord,
            aspect.name,
            color=QColor('white'),
            withBackground=True,
            backgroundOpacity=0.8,
            padding=(MARGIN, MARGIN, MARGIN, MARGIN * 4),
            UI=UI,
            onClickCallback=onClickCellIsAspect,
            onClickCallbackArgs=[aspect],
            hoverable=True,
        ))
        aspectImage = UI.addObject(Image(
            textXCoord + MARGIN * 2, textYCoord,
            MARGIN * 2, MARGIN * 2,
            None,
        ))
        aspectImage.setImage(aspect.pixMapImage)
        cellSettingsStateDialogueObjects.append(textAspect)
        cellSettingsStateDialogueObjects.append(aspectImage)
        textYCoord += textAspect.h
        if textYCoord > UI.height() - textAspect.h:
            textYCoord = startTextYCoord
            textXCoord += 250
    UI.setObjectsVisibility(cellSettingsStateDialogueObjects, False)

    # --- Active state elements
    def insertAndPrepareNextIteration() -> None:
        logging.info("Inserting and preparing for next iteration")
        if multyResearchesCountLeft[0] > 0:
            UI.safeSetAllObjectsVisibility(False)
            UI.safeRepaint()
            renderDelay()
            TI.insertPaper()
        TI.moveMouseInSafePos()
        existingAspects[0].clear()
        freeHexagons[0].clear()
        noneHexagons[0].clear()
        currentLinkMap[0].clear()
        updateDetectingField()
        updateSolving()
        logging.info("Everything prepared to next detecting")
        if inkExhausted[0]:
            # Чернильница пуста: выкладывание отключено, авто-режим останавливаем,
            # следующие записки из инвентаря не достаём
            logging.critical("Ink exhausted: automatic mode stopped")
            multyResearchesCountLeft[0] = 0
            updateCellsImage()
            switchToActiveState()
            notificationsManager.show(inkNotification)
            return
        if multyResearchesCountLeft[0] > 0:
            multyResearchesCountLeft[0] -= 1
            startPuttingLinkMap()
            return
        updateCellsImage()
        switchToActiveState()

    def startPuttingLinkMap() -> None:
        if inkExhausted[0]:
            # Пользователь мог уже пополнить чернильницу: переопределяем поле и решаем заново,
            # чтобы кнопка «Выложить решение» работала без дополнительных действий
            logging.info("Ink was exhausted: re-detecting the field before placing")
            updateDetectingField()
            updateSolving()
            switchToActiveState()
        if inkExhausted[0]:
            # Чернильница пуста: выкладывание отключено, пока пользователь не пополнит чернила
            logging.critical("Ink exhausted: placing is disabled")
            notificationsManager.show(inkNotification)
            return
        # Пользователь запустил выкладывание: показанное сообщение он уже прочитал,
        # а экран должен быть чистым для скриншотов поля
        notificationsManager.hide()
        UI.safeSetAllObjectsVisibility(False)

        onProcessText = Text(
            MARGIN, MARGIN,
            AppState.translatedTexts[TEXTS.waitForSolvingPlacing],
            color=QColor('white'),
            withBackground=True,
            padding=MARGIN,
            UI=UI,  # Передаем UI для корректной инициализации объекта
        )
        UI.safeAddObject(onProcessText)
        UI.safeClearKeyCallbacks()
        UI.safeSetKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.alt], UI.safeExit)

        finalLinkMap = currentLinkMap[0].copy()
        # Remove initial aspects from linkMap
        for aspectCoords in existingAspects[0].keys():
            del finalLinkMap[aspectCoords]

        # Клетки, которые до выкладывания уже были свободными или занятыми аспектами:
        # по ним отслеживается исчерпание чернильницы посреди выкладывания
        cellsKnownBeforePlacing[0] = set(existingAspects[0]) | set(freeHexagons[0])
        placedAspectsCount = [0]

        def checkInkDuringPlacing() -> bool:
            """Проверяет поле каждые INK_CHECK_EVERY_N_PLACED_ASPECTS выложенных аспектов.

            Если маркерная клетка, которая до выкладывания была свободной или занятой аспектом,
            перестала определяться (стала none) — чернила кончились: игра перестала принимать
            аспекты, и выкладывание надо прервать, а не доводить до конца вслепую.
            """
            if not INK_EXHAUSTED_MARKER_CELLS:
                return True  # отслеживание выключено: лишние скриншоты поля не делаем

            placedAspectsCount[0] += 1
            if placedAspectsCount[0] % INK_CHECK_EVERY_N_PLACED_ASPECTS != 0:
                return True

            # Скрываем сообщение о процессе: его фон попал бы на скриншот поля
            UI.safeSetObjectsVisibility([onProcessText], False)
            UI.safeRepaint()
            renderDelay()
            try:
                (detectedAspects, detectedNoneHexagons,
                 detectedFreeHexagons) = TI.getExistingAspectsOnField()
            except Exception as error:
                # Не роняем поток выкладывания из-за ошибки определения: работаем как раньше
                logging.critical(f"Ink check failed, placing continues: {error}")
                UI.safeSetObjectsVisibility([onProcessText], True)
                return True
            UI.safeSetObjectsVisibility([onProcessText], True)

            markers = markersLostSince(cellsKnownBeforePlacing[0], collectFieldMarkers(
                set(detectedAspects), detectedFreeHexagons, detectedNoneHexagons, INK_EXHAUSTED_MARKER_CELLS))
            logging.debug(f"Field markers while placing: {markers!r}")
            if isInkExhausted(markers, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT,
                              INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE):
                logging.critical("Ink exhausted: marker cells disappeared while placing aspects")
                inkExhausted[0] = True
                return False

            existingAspects[0] = detectedAspects
            noneHexagons[0] = detectedNoneHexagons
            freeHexagons[0] = detectedFreeHexagons
            cellsKnownBeforePlacing[0] = set(detectedAspects) | set(detectedFreeHexagons)
            return True

        def abortPlacing(notification: Text) -> None:
            # Не забираем бумагу и не идём к следующему исследованию, а показываем текущее
            # состояние поля, чтобы пользователь пополнил запасы и выложил решение заново.
            multyResearchesCountLeft[0] = 0
            UI.safeRemoveObject(onProcessText)
            updateDetectingField()
            updateSolving()
            switchToActiveState()
            notificationsManager.show(notification)

        def onPuttingAborted(inkWasExhausted: bool = False) -> None:
            if inkWasExhausted:
                logging.critical("Putting aspects aborted: ink exhausted")
            else:
                logging.critical("Putting aspects aborted: not enough aspects in inventory")
            abortPlacing(inkNotification if inkWasExhausted else abortedNotification)

        def startPuttingAspects() -> None:
            logging.info("Putting aspects started...")
            if not TI.fillByLinkMap(finalLinkMap, checkInkDuringPlacing):
                onPuttingAborted(inkExhausted[0])
                return
            logging.info("Putting aspects done")
            TI.takeOutPaper()
            eventsDelay()
            TI.increaseWorkingSlot()
            insertAndPrepareNextIteration()
            UI.safeRemoveObject(onProcessText)

        # Create thread for long operations
        puttingAspectsThread = threading.Thread(
            target=startPuttingAspects)  # run in thread to not blocking keys callbacks
        puttingAspectsThread.start()

    # vars for changing between render functions
    isInUpdatingAspects = [False]
    curUpdatingUid = [0]
    def regenerateLinkMap() -> None:
        if isInUpdatingAspects[0]:
            return
        isInUpdatingAspects[0] = True
        UI.safeSetAllObjectsVisibility(False)
        UI.safeRepaint()
        renderDelay()

        curUpdatingUid[0] += 1
        interruptingFlag = [False]

        def interruptSolving(curUid: int) -> None:  # interrupt solving after LINK_GENERATION_MAX_TIME_MS
            if isInUpdatingAspects[0] and curUid == curUpdatingUid[0]:
                interruptingFlag[0] = True

        UI.setTimeout(LINK_GENERATION_MAX_TIME_MS, interruptSolving, [curUpdatingUid[0]])

        updateDetectingField()
        updateSolving(interruptingFlag)
        switchToActiveState()
        isInUpdatingAspects[0] = False

    # base dialogue
    def onClickSwitchToMultyResearches() -> None:
        switchToMultyResearchesState()

    def onClickDonate() -> None:
        switchToDonateState()

    activeStateDialogueObjects = createButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.solvingCreated],
        [
            (AppState.translatedTexts[TEXTS.Buttons.backToSettings], Scenarios.chooseThaumVersion, [UI]),
            (AppState.translatedTexts[TEXTS.Buttons.regenerateSolving], regenerateLinkMap, []),
            (AppState.translatedTexts[TEXTS.Buttons.placeSolving], startPuttingLinkMap, []),
            (AppState.translatedTexts[TEXTS.Buttons.automaticMode], onClickSwitchToMultyResearches, []),
            (AppState.translatedTexts[TEXTS.Buttons.goToDonate], onClickDonate, []),
        ]
    )

    # --- Notifications (правый нижний угол, отдельная палитра, не переключаются со состояниями)
    notificationsManager = NotificationManager(UI)
    abortedNotification = createNotification(
        UI,
        AppState.translatedTexts[TEXTS.solvingPlacingAborted],
        backgroundColor=NOTIFICATION_BACKGROUND_ERROR,
    )
    inkNotification = createNotification(
        UI,
        AppState.translatedTexts[TEXTS.solvingInkExhausted],
        backgroundColor=NOTIFICATION_BACKGROUND_ERROR,
    )

    # --- Multy researches state elements
    def onClickBack() -> None:
        switchToActiveState()

    def onClickNumber(researchesCount: int) -> None:
        multyResearchesCountLeft[0] = researchesCount
        TI.resetWorkingSlot()
        renderDelay()
        renderDelay()
        insertAndPrepareNextIteration()

    multyResearchesObjects = createButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.startAutomaticMode],
        [
            (AppState.translatedTexts[TEXTS.Buttons.back], onClickBack, []),
            ("1", onClickNumber, [1]), ("2", onClickNumber, [2]), ("3", onClickNumber, [3]),
            ("4", onClickNumber, [4]), ("5", onClickNumber, [5]), ("6", onClickNumber, [6]),
            ("7", onClickNumber, [7]), ("8", onClickNumber, [8]), ("9", onClickNumber, [9]),
            ("10", onClickNumber, [10]), ("11", onClickNumber, [11]), ("12", onClickNumber, [12]),
            ("13", onClickNumber, [13]), ("14", onClickNumber, [14]), ("15", onClickNumber, [15]),
            ("16", onClickNumber, [16]), ("17", onClickNumber, [17]), ("18", onClickNumber, [18]),
            ("19", onClickNumber, [19]), ("20", onClickNumber, [20]), ("21", onClickNumber, [21]),
            ("22", onClickNumber, [22]), ("23", onClickNumber, [23]), ("24", onClickNumber, [24]),
            ("25", onClickNumber, [25]), ("26", onClickNumber, [26]), ("27", onClickNumber, [27]),
        ]
    )

    # --- Donate state elements
    def onClickDonateRussia() -> None:
        QDesktopServices.openUrl(QUrl(DONATE_URL_RUSSIA))

    def onClickDonateGlobal() -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(DONATE_CRYPTO_ID_GLOBAL)

    donateObjects = createButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.donate],
        [
            (AppState.translatedTexts[TEXTS.Buttons.donateGlobal], onClickDonateGlobal, []),
            (AppState.translatedTexts[TEXTS.Buttons.donateRussia], onClickDonateRussia, []),
            (AppState.translatedTexts[TEXTS.Buttons.back], onClickBack, []),
        ]
    )

    # --- Paused state elements
    onPausedText = UI.addObject(Text(
        MARGIN, MARGIN,
        AppState.translatedTexts[TEXTS.programPaused],
        color=QColor('white'),
        withBackground=True,
        padding=MARGIN,
        movable=True,
        UI=UI,
    ))
    pausedStateDialogueObjects = [onPausedText]

    # --- Switch between states functions
    # Уведомления не переключаются вместе с состояниями: любое переключение гасит все объекты
    # сцены (setAllObjectsVisibility(False)), поэтому показанные уведомления возвращаются в конце
    def switchToActiveState() -> None:
        logging.info("Switching to active state")
        UI.clearKeyCallbacks()
        UI.setKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], switchToPausedState)
        UI.setAllObjectsVisibility(False)
        UI.setObjectsVisibility(activeStateDialogueObjects, True)
        UI.setObjectsVisibility(cellsObjects, True)
        exitButtonObject.setVisibility(True)
        notificationsManager.restore()

    def switchToPausedState() -> None:
        logging.info("Switching to paused state")
        UI.clearKeyCallbacks()
        UI.setKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], switchToActiveState)
        UI.setAllObjectsVisibility(False)
        UI.setObjectsVisibility(pausedStateDialogueObjects, True)
        notificationsManager.restore()

    def switchToCellSettingsState() -> None:
        logging.info("Switching to cell settings state")
        UI.clearKeyCallbacks()
        UI.setKeyCallback([KeyboardKeys.n], onClickCellIsNone)
        UI.setKeyCallback([KeyboardKeys.f], onClickCellIsFree)
        UI.setKeyCallback([KeyboardKeys.esc], exitCellDialogue)
        UI.setAllObjectsVisibility(False)
        UI.setObjectsVisibility(cellSettingsStateDialogueObjects, True)
        UI.setObjectsVisibility(cellsObjects, True)
        exitButtonObject.setVisibility(True)
        notificationsManager.restore()

    def switchToMultyResearchesState() -> None:
        logging.info("Switching to multy researches state")
        UI.clearKeyCallbacks()
        UI.setKeyCallback([KeyboardKeys.esc], switchToActiveState)
        UI.setAllObjectsVisibility(False)
        UI.setObjectsVisibility(multyResearchesObjects, True)
        exitButtonObject.setVisibility(True)
        notificationsManager.restore()

    def switchToDonateState() -> None:
        logging.info("Switching to donate state")
        UI.clearKeyCallbacks()
        UI.setKeyCallback([KeyboardKeys.esc], switchToActiveState)
        UI.setAllObjectsVisibility(False)
        UI.setObjectsVisibility(donateObjects, True)
        exitButtonObject.setVisibility(True)
        notificationsManager.restore()

    updateDetectingField()
    updateSolving()
    switchToActiveState()
    logging.debug("Hexagon field with configuring initial aspects showed")
