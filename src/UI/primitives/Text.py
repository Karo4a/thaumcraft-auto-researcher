from typing import Any, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QFont

from UI.primitives.Object import _Object
from UI.primitives.Point import Point
from UI.primitives.Rect import opacityToAlpha
from UI.primitives.values import DEFAULT_FONT, DEFAULT_COLOR, DEFAULT_PADDING
from utils.LinkableValue import editLinkableValue, LinkableValue


class Align(int):
    left: int = Qt.AlignLeft
    right: int = Qt.AlignRight
    top: int = Qt.AlignTop
    bottom: int = Qt.AlignBottom
    center: int = Qt.AlignCenter


class Text(_Object):
    def __init__(
            self,
            x: float,
            y: float,
            text: str,
            font: QFont = QFont(DEFAULT_FONT),
            color: QColor = QColor(DEFAULT_COLOR),
            align: Align = Align.left,
            withBackground: bool = False,
            backgroundColor: QColor = QColor('black'),
            backgroundOpacity: float = 0.5,
            padding: int | tuple[int, int, int, int] = DEFAULT_PADDING,
            movable: bool = False,
            hoverable: bool = False,
            hoverColor: QColor = None,
            onMoveCallback: Callable = None,
            UI: Any = None,
            onClickCallback: Callable = None,
            onClickCallbackArgs: list[Any] = [],
            clickable: bool = None) -> None:
        lines = text.split('\n')
        self.w = max(map(len, lines)) * font.pointSize() / 1.05
        self.h = font.pointSize() * 2.1 * len(lines)
        self.x = x
        self.y = y
        self.text = text
        self.font = font
        self.color = color
        self.align = align
        self.backgroundColor = QColor('transparent')
        self.withBackground = withBackground
        self.onMoveCallback = onMoveCallback
        self.onClickCallback = onClickCallback
        self.onClickCallbackArgs = onClickCallbackArgs
        self.clickable = clickable if clickable is not None else (onClickCallback is not None)
        if self.withBackground:
            self.backgroundColor = backgroundColor
            self.backgroundColor.setAlpha(opacityToAlpha(backgroundOpacity))
            if isinstance(padding, int):
                padding = (padding, padding, padding, padding)
            self.padding = padding
            self.w += padding[1] + padding[3]
            self.h += padding[0] + padding[2]
        if align == Align.center:
            self.x = editLinkableValue(self.x, self.x - self.w / 2)
            self.y = editLinkableValue(self.y, self.y - self.h / 2)
        self.UI = UI
        self.hoverable = hoverable
        self.hoverColor = hoverColor
        self.movable = movable
        if movable:
            if self.UI is None:
                raise TypeError("<class Text>: If argument movable=True, argument UI must be provided!")
            if not isinstance(self.x, LinkableValue):
                self.x = LinkableValue(self.x)
            if not isinstance(self.y, LinkableValue):
                self.y = LinkableValue(self.y)
            pointColor = QColor(self.backgroundColor)
            pointColor.setAlpha(255)
            self.LT = Point(self.x, self.y, movable=True, color=pointColor)
            self.UI.addObject(self.LT)
        super().__init__()
        self._currentColor = self.backgroundColor

    def render(self, painter: QPainter) -> None:
        if not super().render(painter): return
        painter.setFont(self.font)
        if self.withBackground:
            painter.fillRect(int(self.x), int(self.y), int(self.w), int(self.h), self._currentColor)
            painter.drawText(
                int(self.x + self.padding[3]), int(self.y + self.padding[0]),
                int(self.w - self.padding[1] - self.padding[3]), int(self.h - self.padding[0] - self.padding[2]),
                self.align, self.text
            )
        else:
            painter.drawText(int(self.x), int(self.y), int(self.w), int(self.h), self.align, self.text)
        if self.movable:
            self.LT.render(painter)

    def setVisibility(self, state: bool) -> None:
        super().setVisibility(state)
        if self.movable:
            self.LT.setVisibility(state)

    def isHover(self, x: float, y: float) -> bool:
        if not self.visible:
            return False
        return (
                self.x <= x <= self.x + self.w and
                self.y <= y <= self.y + self.h
        )

    def setColor(self, color: QColor) -> None:
        super().setColor(color)
        self._currentColor = self.backgroundColor

    def setText(self, text: str) -> None:
        self.text = text
        lines = text.split('\n')
        self.w = max(map(len, lines)) * self.font.pointSize() / 1.05
        self.h = self.font.pointSize() * 2 * len(lines)
        if self.withBackground:
            self.w += self.padding[1] + self.padding[3]
            self.h += self.padding[0] + self.padding[2]

    def updateHoverState(self, x: float, y: float, isMouseRelease: bool = False) -> None:
        self._updateHoverState(x, y, isMouseRelease, "backgroundColor" if self.withBackground else "color")

    def _setCurrentColor(self, color: QColor) -> None:
        self._currentColor = color
