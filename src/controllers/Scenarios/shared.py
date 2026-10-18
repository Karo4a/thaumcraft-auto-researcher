from typing import Callable, Any

from PyQt5.QtGui import QColor

from UI.OverlayUI import OverlayUI, KeyboardKeys
from UI.primitives import Text
from configs.translations import TEXTS
from utils import AppState
from utils.LinkableValue import LinkableCoord, editLinkableValue
from configs.constants import MARGIN


PointTextAnchor: LinkableCoord = LinkableCoord(MARGIN, MARGIN)

# --- Notifications palette (отличается от палитры обычных диалогов сценариев)
NOTIFICATION_BACKGROUND_INFO: QColor = QColor('black')
NOTIFICATION_BACKGROUND_ERROR: QColor = QColor('darkred')
NOTIFICATION_BACKGROUND_OPACITY: float = 0.8


def createButtonsAndText(
        UI: OverlayUI, text: str,
        buttons: list[tuple[str, Callable, list[Any]]],
        x: int = PointTextAnchor.x, y: int = PointTextAnchor.y,
        movable: bool = True,
) -> list[Text]:
    mainText = Text(
        x, y,
        text,
        color=QColor('white'),
        withBackground=True,
        padding=MARGIN,
        movable=movable,
        UI=UI,
    )
    buttonsElements: list[Text] = []

    def onTextMoving() -> None:
        xCoord = mainText.x
        yCoord = mainText.y + mainText.h + MARGIN
        startXCoord = xCoord
        for buttonElement in buttonsElements:
            buttonElement.x = xCoord
            buttonElement.y = yCoord
            xCoord += buttonElement.w + MARGIN
            if xCoord > UI.width() - buttonElement.w:
                yCoord += buttonElement.h + MARGIN
                xCoord = startXCoord

    mainText.onMoveCallback = onTextMoving
    if movable:
        mainText.LT.onMoveCallback = onTextMoving
    UI.addObject(mainText)

    xCoord = mainText.x
    yCoord = mainText.y + mainText.h + MARGIN
    startXCoord = xCoord
    for (buttonText, buttonCallback, buttonArgs) in buttons:
        buttonElement = Text(
            xCoord,
            yCoord,
            buttonText,
            color=QColor('white'),
            withBackground=True,
            padding=MARGIN,
            UI=UI,
            hoverable=True,
            clickable=True,
            onClickCallback=buttonCallback,
            onClickCallbackArgs=buttonArgs,
        )
        UI.addObject(buttonElement)
        buttonsElements.append(buttonElement)
        xCoord += buttonElement.w + MARGIN
        if xCoord > UI.width() - buttonElement.w:
            yCoord += buttonElement.h + MARGIN
            xCoord = startXCoord

    return [mainText, *buttonsElements]


def createNextBackButtonsAndText(
        UI: OverlayUI,
        text: str,
        nextCallback: Callable | None,
        nextCallbackArgs: list[Any],
        backCallback: Callable | None,
        backCallbackArgs: list[Any],
        overrideNextText: str = None,
        overrideBackText: str = None,
) -> tuple[Text, Text | None, Text | None]:
    buttonsConfig: list[tuple[str, Callable, list[Any]]] = []
    if backCallback is not None:
        buttonsConfig.append((
            overrideBackText or AppState.translatedTexts[TEXTS.Buttons.backArrowed],
            backCallback,
            backCallbackArgs,
        ))
        UI.setKeyCallback([KeyboardKeys.backspace], backCallback, *backCallbackArgs)
    if nextCallback is not None:
        buttonsConfig.append((
            overrideNextText or AppState.translatedTexts[TEXTS.Buttons.nextArrowed],
            nextCallback,
            nextCallbackArgs,
        ))
        UI.setKeyCallback([KeyboardKeys.enter], nextCallback, *nextCallbackArgs)
    elements = createButtonsAndText(UI, text, buttonsConfig)
    return elements[0], elements[1] if len(elements) > 1 else None, elements[2] if len(elements) > 2 else None


def placeNotification(notification: Text, uiWidth: float, uiHeight: float, margin: int = MARGIN) -> None:
    """Ставит уведомление в правый нижний угол экрана, не вылезая за его границы."""
    notification.x = editLinkableValue(notification.x, max(margin, uiWidth - margin - notification.w))
    notification.y = editLinkableValue(notification.y, max(margin, uiHeight - margin - notification.h))


def createNotification(
        UI: OverlayUI,
        text: str,
        backgroundColor: QColor = NOTIFICATION_BACKGROUND_INFO,
        margin: int = MARGIN,
) -> Text:
    """Создаёт (но не показывает) уведомление в правом нижнем углу экрана.

    Уведомления не являются диалогами: они не переключаются вместе со состояниями сценария,
    показываются поверх игры на время и используют собственную цветовую палитру
    (ошибки — NOTIFICATION_BACKGROUND_ERROR), чтобы не путаться с обычными окнами.
    """
    notification = Text(
        margin, margin,
        text,
        color=QColor('white'),
        withBackground=True,
        backgroundColor=backgroundColor,
        backgroundOpacity=NOTIFICATION_BACKGROUND_OPACITY,
        padding=MARGIN,
        UI=UI,
    )
    placeNotification(notification, UI.w, UI.h, margin)
    return notification
