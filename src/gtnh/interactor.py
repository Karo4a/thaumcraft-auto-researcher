import logging
import math
import time
from typing import Callable

from PIL import Image
from PyQt5.QtGui import QColor

from UI.OverlayUI import OverlayUI
from configs.constants import UNKNOWN_ASPECT_IMAGE_PATH
from controllers.Aspect import Aspect
from controllers.Point import P
from controllers.ThaumInteractor import ThaumInteractor
from gtnh.aspect import GtnhAspect
from gtnh.constants import THAUM_ASPECTS_INVENTORY_SLOTS_X, \
    THAUM_ASPECTS_INVENTORY_SLOTS_Y, DELAY_BETWEEN_EVENTS
from gtnh.mixing import planMixing
from gtnh.recognition import aspects_count, filterByMaxConfidence, splitAspectsAndDigits
from logic.Neurolink import Neurolink, ObjectPrediction


def eventsDelay():
    time.sleep(DELAY_BETWEEN_EVENTS)


class GtnhThaumInteractor(ThaumInteractor):
    rectAspectsListingLT2: P
    rectAspectsListingRB2: P

    def __init__(self, UI: OverlayUI, controlsConfig: dict[str, dict[str, float]],
                 aspectsRecipes: dict[str, list[str, str]], orderedAvailableAspects: list[str]):
        self.UI = UI

        c = controlsConfig
        self.pointWritingMaterials = P(c['pointWritingMaterials']['x'], c['pointWritingMaterials']['y'])
        self.pointPapers = P(c['pointPapers']['x'], c['pointPapers']['y'])
        self.pointSafePosition = P((self.pointPapers.x + self.pointWritingMaterials.x) / 2, self.pointPapers.y)
        self.rectAspectsListingLT = P(c['rectAspectsListingLT']['x'], c['rectAspectsListingLT']['y'])
        self.rectAspectsListingRB = P(c['rectAspectsListingRB']['x'], c['rectAspectsListingRB']['y'])
        self.rectAspectsListingLT2 = P(c['rectAspectsListingLT2']['x'], c['rectAspectsListingLT2']['y'])
        self.rectAspectsListingRB2 = P(c['rectAspectsListingRB2']['x'], c['rectAspectsListingRB2']['y'])
        self.rectInventoryLT = P(c['rectInventoryLT']['x'], c['rectInventoryLT']['y'])
        self.rectInventoryRB = P(c['rectInventoryRB']['x'], c['rectInventoryRB']['y'])
        self.rectHexagonsCC = P(c['rectHexagonsCC']['x'], c['rectHexagonsCC']['y'])
        self.hexagonSlotSizeY = c['hexagonSlotSizeY']
        self.hexagonSlotSizeX = self.hexagonSlotSizeY * math.cos(math.pi / 6)
        self.increaseWorkingSlot()

        self.unknownAspectImage = self.loadImage(UNKNOWN_ASPECT_IMAGE_PATH)
        self.recipes = aspectsRecipes

        self.allAspects = [GtnhAspect(orderedAvailableAspects[i], i) for i in range(len(orderedAvailableAspects))]
        self.loadAspectsImages()

        logging.info(f"GTNH ThaumcraftInteractor successfully initialized")
        logging.info(f"All known aspects:     {self.allAspects}")
        logging.info(f"All available aspects: {self.availableAspects}")

    def getRectAspectListingLTbyNumber(self, rectAspectNumber: int) -> P:
        match rectAspectNumber:
            case 0:
                return self.rectAspectsListingLT
            case 1:
                return self.rectAspectsListingLT2
        raise ValueError(f"Unknown rectAspectNumber: {rectAspectNumber}")

    def getRectAspectListingRBbyNumber(self, rectAspectNumber: int) -> P:
        match rectAspectNumber:
            case 0:
                return self.rectAspectsListingRB
            case 1:
                return self.rectAspectsListingRB2
        raise ValueError(f"Unknown rectAspectNumber: {rectAspectNumber}")

    def inventoryCellCoordsToPixelCoords(self, cellX: int, cellY: int, rectAspectNumber: int) -> P:
        rectAspectsListingLT = self.getRectAspectListingLTbyNumber(rectAspectNumber)
        rectAspectsListingRB = self.getRectAspectListingRBbyNumber(rectAspectNumber)
        areaWidth = rectAspectsListingRB.x - rectAspectsListingLT.x
        areaHeight = rectAspectsListingRB.y - rectAspectsListingLT.y
        slotWidth = areaWidth / THAUM_ASPECTS_INVENTORY_SLOTS_X
        slotHeight = areaHeight / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        return P(
            rectAspectsListingLT.x + slotWidth * (cellX + 0.5),
            rectAspectsListingLT.y + slotHeight * (cellY + 0.5)
        )

    def inventoryCellCoordsToPixelBoundingBox(self, cellX: int, cellY: int, rectAspectNumber: int) -> tuple[float, float, float, float]:
        rectAspectsListingLT = self.getRectAspectListingLTbyNumber(rectAspectNumber)
        rectAspectsListingRB = self.getRectAspectListingRBbyNumber(rectAspectNumber)
        areaWidth = rectAspectsListingRB.x - rectAspectsListingLT.x
        areaHeight = rectAspectsListingRB.y - rectAspectsListingLT.y
        slotWidth = areaWidth / THAUM_ASPECTS_INVENTORY_SLOTS_X
        slotHeight = areaHeight / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        x = rectAspectsListingLT.x + slotWidth * cellX
        y = rectAspectsListingLT.y + slotHeight * cellY
        return x, y, x + slotWidth, y + slotHeight

    def takeAspectByCellCoords(self, cellX, cellY, rectAspectNumber):
        aspectPoint = self.inventoryCellCoordsToPixelCoords(cellX, cellY, rectAspectNumber)
        logging.info(f"Take aspect from cell ({cellX, cellY}), coordinates: {aspectPoint}")
        aspectPoint.hold()
        self._showDebugClick(aspectPoint, QColor('blue'))

    def getCellIdxByCellCoords(self, cellX: int, cellY: int) -> int:
        return cellX * THAUM_ASPECTS_INVENTORY_SLOTS_Y + cellY

    def getAspectByCellCoords(self, cellX: int, cellY: int, rectAspectNumber: int) -> Aspect | None:
        for aspect in self.availableAspects:
            if aspect.cellX == cellX and aspect.cellY == cellY and aspect.rectAspectsNumber == rectAspectNumber:
                return aspect
        return None

    def setAspectIntoAvailables(self, aspect: Aspect, cellX: int, cellY: int, rectAspectNumber: int):
        prevAspect = self.getAspectByCellCoords(cellX, cellY, rectAspectNumber)
        aspect.cellX = cellX
        aspect.cellY = cellY
        aspect.rectAspectsNumber = rectAspectNumber
        logging.info(f"Adding new aspect to availables: {aspect}. Previous aspect in this cell: {prevAspect}")

        if prevAspect is not None:
            if prevAspect == aspect:
                logging.info(f"Aspects is equal. Nothing to change")
                return
            aspectIdx = self.getAvailableAspectIdx(prevAspect)
            prevAspect.count = None
            prevAspect.cellX = None
            prevAspect.cellY = None
            prevAspect.rectAspectsNumber = None
            self.availableAspects[aspectIdx] = aspect
            logging.info(f"Aspect {prevAspect} successfully changed to {aspect} on idx {aspectIdx}")
        else:
            cellIdx = self.getCellIdxByCellCoords(cellX, cellY)
            cellsBeforeCount = 0
            for a in self.availableAspects:
                if self.getCellIdxByCellCoords(a.cellX, a.cellY) < cellIdx:
                    cellsBeforeCount += 1
            self.availableAspects.insert(cellsBeforeCount, aspect)
            logging.info(f"Aspect {aspect} successfully inserted on idx {cellsBeforeCount}")

        def removeAspectDuplicates():
            for a in self.availableAspects:
                if a.uid == aspect.uid and a.cellX != cellX and a.cellY != cellY:
                    self.availableAspects.remove(a)
                    removeAspectDuplicates()
                    break

        removeAspectDuplicates()

    def takeAspect(self, aspect: Aspect):
        if not self.mixAspect(aspect, 1):
            logging.critical(f"Cannot mix aspect {aspect.name}. Take skipped")
            return
        logging.info(f"Take aspect {aspect}...")
        self.takeAspectByCellCoords(aspect.cellX, aspect.cellY, aspect.rectAspectsNumber)
        aspect.count -= 1

    def mixAspect(self, aspect: Aspect, targetCount=3) -> bool:
        """
        Создаёт аспект миксом по рецепту (GTNH: drag/right-click).
        Возвращает True, если микс выполнен или аспекта уже достаточно, False — если микс невозможен.
        """
        if (aspect.count or 0) >= targetCount:
            return True
        plan = planMixing(aspect, targetCount, self.getAspectByName, self.getAspectRecipeByName)
        if plan is None:
            return False
        for aspectRecipe, mixingTimes in plan:
            aspect1, aspect2 = map(lambda name: self.getAspectByName(name),
                                   self.getAspectRecipeByName(aspectRecipe.name))
            if aspect1.cellX is None or aspect2.cellX is None:
                logging.critical(f"Cannot mix {aspectRecipe.name}: ingredient has no cell coords "
                                 f"({aspect1.name}: {aspect1.cellX},{aspect1.cellY}; "
                                 f"{aspect2.name}: {aspect2.cellX},{aspect2.cellY})")
                return False
            # Защита от особенности planMixing: общий ингредиент может быть недосчитан
            if (aspect1.count or 0) < mixingTimes or (aspect2.count or 0) < mixingTimes:
                logging.critical(f"Not enough aspects to mix {aspectRecipe.name}: x{mixingTimes} of "
                                 f"{aspect1.name}({aspect1.count}) and {aspect2.name}({aspect2.count})")
                return False
            self.takeAspectByCellCoords(aspect1.cellX, aspect1.cellY, aspect1.rectAspectsNumber)
            aspect2_point = self.inventoryCellCoordsToPixelCoords(aspect2.cellX, aspect2.cellY, aspect2.rectAspectsNumber)
            eventsDelay()
            for _ in range(mixingTimes - 1):
                aspect2_point.click('right')
                eventsDelay()
            aspect2_point.release()
            eventsDelay()

            aspectRecipe.count += mixingTimes
            aspect1.count -= mixingTimes
            aspect2.count -= mixingTimes
        return True

    def fillByLinkMap(self, aspectsMap: dict[tuple[int, int], str]):
        logging.info(f"Filling aspects by link map: {aspectsMap}")

        aspectsListMap = list(aspectsMap.items())
        aspectsListMap.sort(key=lambda pair: self.getAspectByName(pair[1]).uid)
        logging.debug(f"Sorted aspects link map: {aspectsListMap}")

        for coords, aspectName in aspectsListMap:
            aspect = self.getAspectByName(aspectName)
            self.takeAspect(aspect)
            eventsDelay()
            self.putAspect(*coords)
            eventsDelay()

    def updateAvailableAspectsInInventory(self, onFinishCallback: Callable, callbackArgs=[]):
        logging.info("Detecting available aspects in inventory... (GTNH)")
        self.availableAspects = []

        debugHighlightingRect = self._addDebugHighlightingRect()
        self.UI.repaint()

        def detectAspects(screenshotImage: Image.Image, rectAspectsNumber: int):
            rectLT = self.getRectAspectListingLTbyNumber(rectAspectsNumber)
            rectRB = self.getRectAspectListingRBbyNumber(rectAspectsNumber)
            slotWidth = (rectRB.x - rectLT.x) / THAUM_ASPECTS_INVENTORY_SLOTS_X
            slotHeight = (rectRB.y - rectLT.y) / THAUM_ASPECTS_INVENTORY_SLOTS_Y

            logging.info("Wait for prediction aspects")
            predictions: list[ObjectPrediction] = Neurolink.predict_inventory_aspects(screenshotImage)
            predictionsAspect, predictionsDigit = splitAspectsAndDigits(predictions)
            predictionsAspect = filterByMaxConfidence(predictionsAspect)
            logging.info(f"Aspects predictions: {predictionsAspect}")

            logging.info("Wait for prediction counts")
            count_predictions = aspects_count(predictionsAspect, predictionsDigit)
            logging.info(f"Counts predictions:  {count_predictions}")

            for prediction in predictionsAspect:
                try:
                    aspect = self.getAspectByName(prediction.predictionName)
                    aspect_count = count_predictions[prediction.predictionName]
                except ValueError:
                    continue
                aspect.cellX = int(prediction.x // slotWidth)
                aspect.cellY = int(prediction.y // slotHeight)
                aspect.count = aspect_count or 0
                aspect.rectAspectsNumber = rectAspectsNumber
                logging.debug(f"Aspect: {aspect}, ({aspect.cellX}, {aspect.cellY}), rect: {rectAspectsNumber}")
                self.availableAspects.append(aspect)

            logging.info(f"All found aspects: {self.availableAspects}")

        def exitWithSort():
            self.UI.removeObject(debugHighlightingRect)
            self.availableAspects.sort(key=lambda a: a.uid)
            logging.info("All detected available aspects was sorted")
            self.logAvailableAspects()
            onFinishCallback(*callbackArgs)

        rects = [
            (self.rectAspectsListingLT, self.rectAspectsListingRB),
            (self.rectAspectsListingLT2, self.rectAspectsListingRB2),
        ]
        for rectAspectNumber, (rectLT, rectRB) in enumerate(rects):
            screenshotImage = self.takeScreenshot(
                rectLT.x, rectLT.y,
                rectRB.x, rectRB.y,
                debugHighlightingRect
            )
            detectAspects(screenshotImage, rectAspectNumber)
        exitWithSort()
