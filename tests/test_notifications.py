import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from UI.primitives.Rect import opacityToAlpha
from configs.constants import MARGIN
from controllers.Scenarios.shared import (
    createNotification,
    placeNotification,
    NOTIFICATION_BACKGROUND_ERROR,
    NOTIFICATION_BACKGROUND_INFO,
    NOTIFICATION_BACKGROUND_OPACITY,
)


class FakeNotification:
    """Минимальный объект для placeNotification: функция работает только с x/y/w/h."""

    def __init__(self, x=0, y=0, w=300, h=100):
        self.x = x
        self.y = y
        self.w = w
        self.h = h


class PlaceNotificationTest(unittest.TestCase):
    def test_notification_goes_to_bottom_right_corner(self):
        notification = FakeNotification(w=300, h=100)
        placeNotification(notification, 1920, 1080)
        self.assertEqual(notification.x, 1920 - MARGIN - 300)
        self.assertEqual(notification.y, 1080 - MARGIN - 100)

    def test_notification_does_not_intersect_active_dialogue(self):
        # Регресс: сообщение об аборте ставилось в (MARGIN, MARGIN) поверх активного диалога
        dialogueX, dialogueY, dialogueW, dialogueH = MARGIN, MARGIN, 900, 250
        notification = FakeNotification(w=900, h=100)
        placeNotification(notification, 1920, 1080)
        intersects = (
                notification.x < dialogueX + dialogueW and dialogueX < notification.x + notification.w and
                notification.y < dialogueY + dialogueH and dialogueY < notification.y + notification.h
        )
        self.assertFalse(intersects)

    def test_notification_stays_on_screen_when_there_is_no_room(self):
        notification = FakeNotification(w=300, h=100)
        placeNotification(notification, 100, 60)
        self.assertEqual(notification.x, MARGIN)
        self.assertEqual(notification.y, MARGIN)

    def test_notification_size_is_not_changed(self):
        notification = FakeNotification(w=300, h=100)
        placeNotification(notification, 1920, 1080)
        self.assertEqual((notification.w, notification.h), (300, 100))


class CreateNotificationTest(unittest.TestCase):
    def test_notification_is_created_in_bottom_right_corner(self):
        UI = SimpleNamespace(w=1920, h=1080)
        notification = createNotification(UI, "some message", backgroundColor=NOTIFICATION_BACKGROUND_ERROR)
        self.assertEqual(notification.text, "some message")
        self.assertEqual(notification.x, 1920 - MARGIN - notification.w)
        self.assertEqual(notification.y, 1080 - MARGIN - notification.h)

    def test_error_notification_uses_its_own_palette(self):
        UI = SimpleNamespace(w=1920, h=1080)
        errorNotification = createNotification(UI, "error", backgroundColor=NOTIFICATION_BACKGROUND_ERROR)
        infoNotification = createNotification(UI, "info", backgroundColor=NOTIFICATION_BACKGROUND_INFO)
        self.assertEqual(errorNotification.backgroundColor.name(), NOTIFICATION_BACKGROUND_ERROR.name())
        self.assertEqual(infoNotification.backgroundColor.name(), NOTIFICATION_BACKGROUND_INFO.name())
        self.assertNotEqual(errorNotification.backgroundColor.name(), infoNotification.backgroundColor.name())
        self.assertEqual(
            errorNotification.backgroundColor.alpha(),
            opacityToAlpha(NOTIFICATION_BACKGROUND_OPACITY),
        )

    def test_notification_is_not_added_to_ui(self):
        # Уведомление показывается отдельно (showNotification), а не вместе с диалогами состояний
        created = []

        class FakeUI:
            w = 1920
            h = 1080

            def addObject(self, obj):
                created.append(obj)
                return obj

        notification = createNotification(FakeUI(), "message")
        self.assertEqual(created, [])
        self.assertFalse(notification.movable)


if __name__ == "__main__":
    unittest.main()