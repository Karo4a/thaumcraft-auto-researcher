import logging
from math import cos, pi, sin

from PyQt5.QtGui import QColor

from UI.primitives import Point, Line, Rect
from configs.constants import THAUM_HEXAGONS_SLOTS_COUNT
from configs.translations import TEXTS
from controllers import Scenarios
from controllers.Scenarios.shared import createNextBackButtonsAndText
from gtnh.constants import THAUM_ASPECTS_INVENTORY_SLOTS_X, THAUM_ASPECTS_INVENTORY_SLOTS_Y
from utils import AppState
from utils.LinkableValue import LinkableCoord, LinkableValue


def confirmThaumWindowSlots(UI, LTx, LTy, RBx, RBy):
    thaumWindowWidth = RBx - LTx
    thaumWindowHeight = RBy - LTy
    logging.info(
        f"Thaum window configured at: ({int(LTx)}, {int(LTy)}) x ({int(RBx)}, {int(RBy)}), width={thaumWindowWidth}, height={thaumWindowHeight}")

    UI.clearAll()
    UI.createExitButton()

    def saveControls():
        AppState.saveThaumWindowControls(
            pointWritingMaterials, pointPapers,
            rectAspectsListing.LT, rectAspectsListing.RB,
            rectAspectsListing2.LT, rectAspectsListing2.RB,
            rectInventory.LT, rectInventory.RB, rectHexagonsCC,
            (rectHexagonsCC.y - rectHexagonsTy) / (THAUM_HEXAGONS_SLOTS_COUNT // 2)
        )
        Scenarios.chooseThaumVersion(UI)

    createNextBackButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.confirmThaumWindowSlots],
        saveControls, [],
        Scenarios.configureThaumWindowCoords, [UI],
    )

    # Slots
    Ws = thaumWindowWidth / 15
    Hs = thaumWindowHeight / 10
    topSlotsY = LinkableValue(LTy + Hs * 0.7)  # GTNH
    pointWritingMaterials = UI.addObject(
        Point(LTx + Ws * 4.3, topSlotsY, movable=True, color=QColor('yellow')))  # writing materials
    pointPapers = UI.addObject(Point(LTx + Ws * 10.65, topSlotsY, movable=True, color=QColor('yellowgreen')))  # scrolls

    rectAspectsLT = LinkableCoord(LTx + Ws * 0.375, LTy + Hs * 0.375)
    rectAspectsRB = LinkableCoord(LTx + Ws * 3.3, LTy + Hs * 7.2)
    UI.addObject(
        Line(rectAspectsLT.x, rectAspectsLT.y, rectAspectsRB.x, rectAspectsRB.y, dashed=True, color=QColor('brown')))
    UI.addObject(
        Line(rectAspectsRB.x, rectAspectsLT.y, rectAspectsLT.x, rectAspectsRB.y, dashed=True, color=QColor('brown')))
    rectAspectsListing = UI.addObject(
        Rect(rectAspectsLT.x, rectAspectsLT.y, rectAspectsRB.x, rectAspectsRB.y, dashed=True, color=QColor('lime')))

    verticalListingLines = []
    for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
        xVal = rectAspectsLT.x + x * rectAspectsListing.w / THAUM_ASPECTS_INVENTORY_SLOTS_X
        line = Line(xVal, rectAspectsLT.y, xVal, rectAspectsRB.y, dashed=True, color=QColor('lime'), width=1)
        verticalListingLines.append(line)
        UI.addObject(line)
    horizontalListingLines = []
    for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
        yVal = rectAspectsLT.y + y * rectAspectsListing.h / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        line = Line(rectAspectsLT.x, yVal, rectAspectsRB.x, yVal, dashed=True, color=QColor('lime'), width=1)
        horizontalListingLines.append(line)
        UI.addObject(line)

    def updateListingRectCoords():
        rectW = rectAspectsRB.x - rectAspectsLT.x
        rectH = rectAspectsRB.y - rectAspectsLT.y
        for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
            xVal = rectAspectsLT.x + x * rectW / THAUM_ASPECTS_INVENTORY_SLOTS_X
            verticalListingLines[x - 1].S.x = xVal
            verticalListingLines[x - 1].E.x = xVal
        for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
            yVal = rectAspectsLT.y + y * rectH / THAUM_ASPECTS_INVENTORY_SLOTS_Y
            horizontalListingLines[y - 1].S.y = yVal
            horizontalListingLines[y - 1].E.y = yVal

    UI.addObject(Point(rectAspectsLT.x, rectAspectsLT.y, movable=True, onMoveCallback=updateListingRectCoords))
    UI.addObject(Point(rectAspectsRB.x, rectAspectsRB.y, movable=True,
                       onMoveCallback=updateListingRectCoords))  # aspects listing rectangle

    # v GTNH: second aspects listing zone v #
    rectAspectsLT2 = LinkableCoord(LTx + Ws * 11.75, LTy + Hs * 0.375)
    rectAspectsRB2 = LinkableCoord(LTx + Ws * 14.625, LTy + Hs * 7.2)
    UI.addObject(
        Line(rectAspectsLT2.x, rectAspectsLT2.y, rectAspectsRB2.x, rectAspectsRB2.y, dashed=True, color=QColor('brown')))
    UI.addObject(
        Line(rectAspectsRB2.x, rectAspectsLT2.y, rectAspectsLT2.x, rectAspectsRB2.y, dashed=True, color=QColor('brown')))
    rectAspectsListing2 = UI.addObject(
        Rect(rectAspectsLT2.x, rectAspectsLT2.y, rectAspectsRB2.x, rectAspectsRB2.y, dashed=True, color=QColor('orange')))

    verticalListingLines2 = []
    for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
        xVal = rectAspectsLT2.x + x * rectAspectsListing2.w / THAUM_ASPECTS_INVENTORY_SLOTS_X
        line = Line(xVal, rectAspectsLT2.y, xVal, rectAspectsRB2.y, dashed=True, color=QColor('orange'), width=1)
        verticalListingLines2.append(line)
        UI.addObject(line)
    horizontalListingLines2 = []
    for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
        yVal = rectAspectsLT2.y + y * rectAspectsListing2.h / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        line = Line(rectAspectsLT2.x, yVal, rectAspectsRB2.x, yVal, dashed=True, color=QColor('orange'), width=1)
        horizontalListingLines2.append(line)
        UI.addObject(line)

    def updateListingRectCoords2():
        rectW = rectAspectsRB2.x - rectAspectsLT2.x
        rectH = rectAspectsRB2.y - rectAspectsLT2.y
        for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
            xVal = rectAspectsLT2.x + x * rectW / THAUM_ASPECTS_INVENTORY_SLOTS_X
            verticalListingLines2[x - 1].S.x = xVal
            verticalListingLines2[x - 1].E.x = xVal
        for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
            yVal = rectAspectsLT2.y + y * rectH / THAUM_ASPECTS_INVENTORY_SLOTS_Y
            horizontalListingLines2[y - 1].S.y = yVal
            horizontalListingLines2[y - 1].E.y = yVal

    UI.addObject(Point(rectAspectsLT2.x, rectAspectsLT2.y, movable=True, onMoveCallback=updateListingRectCoords2))
    UI.addObject(Point(rectAspectsRB2.x, rectAspectsRB2.y, movable=True,
                       onMoveCallback=updateListingRectCoords2))  # aspects listing rectangle 2
    # ^ GTNH ^ #

    rectLT = LinkableCoord(LTx + Ws * 3.6, LTy + Hs * 9.2)
    rectRB = LinkableCoord(LTx + Ws * 11.4, LTy + Hs * 11.8)
    UI.addObject(Line(rectLT.x, rectLT.y, rectRB.x, rectRB.y, dashed=True, color=QColor('brown')))
    UI.addObject(Line(rectRB.x, rectLT.y, rectLT.x, rectRB.y, dashed=True, color=QColor('brown')))
    rectInventory = UI.addObject(Rect(rectLT.x, rectLT.y, rectRB.x, rectRB.y, dashed=True, color=QColor('purple')))
    UI.addObject(Point(rectLT.x, rectLT.y, movable=True))
    UI.addObject(Point(rectRB.x, rectRB.y, movable=True))  # inventory rectangle

    rectHexagonsCC = LinkableCoord(LTx + Ws * 7.5, LTy + Hs * 5)  # GTNH
    rectHexagonsTy = LinkableValue(LTy + Hs * 2)  # GTNH
    verticalHexagonsLines = []
    deg30HexagonsLines = []
    deg60HexagonsLines = []
    for i in range(THAUM_HEXAGONS_SLOTS_COUNT):
        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        verticalHexagonsLines.append(line)
        UI.addObject(line)

        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        deg30HexagonsLines.append(line)
        UI.addObject(line)

        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        deg60HexagonsLines.append(line)
        UI.addObject(line)

    def updateHexagonsCoords():
        rad = rectHexagonsCC.y - rectHexagonsTy
        slotSizeY = rad / (THAUM_HEXAGONS_SLOTS_COUNT // 2)
        slotSizeX = slotSizeY * cos(pi / 6)
        for i in range(-THAUM_HEXAGONS_SLOTS_COUNT // 2, THAUM_HEXAGONS_SLOTS_COUNT // 2 + 1):
            idx = i + THAUM_HEXAGONS_SLOTS_COUNT // 2
            verticalHexagonsLines[idx].S.x = rectHexagonsCC.x + i * slotSizeX
            verticalHexagonsLines[idx].E.x = rectHexagonsCC.x + i * slotSizeX
            verticalHexagonsLines[idx].S.y = rectHexagonsCC.y - rad + abs(i) * slotSizeY / 2
            verticalHexagonsLines[idx].E.y = rectHexagonsCC.y + rad - abs(i) * slotSizeY / 2

            deg30HexagonsLines[idx].S.x = rectHexagonsCC.x + cos(pi / 6) * rad + (i < 0) * i * slotSizeX
            deg30HexagonsLines[idx].E.x = rectHexagonsCC.x - cos(pi / 6) * rad + (i > 0) * i * slotSizeX
            deg30HexagonsLines[idx].S.y = rectHexagonsCC.y + sin(pi / 6) * rad - (i < 0) * i * slotSizeY / 2 - (
                    i > 0) * i * slotSizeY
            deg30HexagonsLines[idx].E.y = rectHexagonsCC.y - sin(pi / 6) * rad - (i > 0) * i * slotSizeY / 2 - (
                    i < 0) * i * slotSizeY

            deg60HexagonsLines[idx].S.x = -deg30HexagonsLines[idx].S.x + rectHexagonsCC.x * 2
            deg60HexagonsLines[idx].E.x = -deg30HexagonsLines[idx].E.x + rectHexagonsCC.x * 2
            deg60HexagonsLines[idx].S.y = deg30HexagonsLines[idx].S.y
            deg60HexagonsLines[idx].E.y = deg30HexagonsLines[idx].E.y

    updateHexagonsCoords()

    UI.addObject(Point(rectHexagonsCC.x, rectHexagonsCC.y, movable=True,
                       onMoveCallback=updateHexagonsCoords))
    UI.addObject(Point(rectHexagonsCC.x, rectHexagonsTy, movable=True,
                       onMoveCallback=updateHexagonsCoords))  # hexagons rectangle
    logging.info("Configuring Thaum controls coordinates in window dialogue successfully showed")
