import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from UI.primitives.Rect import opacityToAlpha
from configs import constants as constantsModule
from configs.constants import MARGIN, NOTIFICATION_DISPLAY_TIME_MS
from controllers.Scenarios.shared import (
    createNotification,
    placeNotification,
    NotificationManager,
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


class FakeOverlayUI:
    """Заглушка OverlayUI: менеджер пользуется только показом, скрытием, видимостью и таймерами.

    Поведение совпадает с настоящим OverlayUI: addObject дописывает объект, но не возвращает
    ему видимость (это и был баг «после паузы новые уведомления не показываются»),
    setAllObjectsVisibility гасит всё, включая уведомления.
    """

    def __init__(self):
        self.w = 1920
        self.h = 1080
        self.objects = []
        self.timers = []  # (timeoutMs, callback, args)

    def safeAddObject(self, obj):
        self.objects.append(obj)

    def safeRemoveObject(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)

    def setObjectsVisibility(self, objects, state):
        for obj in objects:
            obj.setVisibility(state)

    def setAllObjectsVisibility(self, state):
        for obj in self.objects:
            obj.setVisibility(state)

    def setTimeout(self, timeoutMs, callback, args=[], kwargs={}, onChangeCallback=lambda timeLeft: None):
        self.timers.append((timeoutMs, callback, list(args)))

    def fireTimers(self):
        """Проигрывает все зарегистрированные таймеры (как timerEvent в OverlayUI)."""
        timers, self.timers = self.timers, []
        for timeoutMs, callback, args in timers:
            callback(*args)


class NotificationManagerTest(unittest.TestCase):
    def setUp(self):
        self.UI = FakeOverlayUI()

    def createManager(self):
        return NotificationManager(self.UI)

    def create(self, text="message"):
        return createNotification(self.UI, text, backgroundColor=NOTIFICATION_BACKGROUND_ERROR)

    def test_show_adds_notification_and_registers_its_display_time(self):
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        self.assertIn(notification, self.UI.objects)
        self.assertTrue(notification.visible)
        self.assertEqual([timeoutMs for timeoutMs, _, _ in self.UI.timers], [NOTIFICATION_DISPLAY_TIME_MS])

    def test_notification_display_time_is_ten_seconds(self):
        self.assertEqual(NOTIFICATION_DISPLAY_TIME_MS, 1000 * 10)

    def test_old_constant_name_is_gone(self):
        # Регресс: константа называлась по конкретному сообщению, а не по времени показа уведомления
        self.assertFalse(hasattr(constantsModule, "SOLVING_ABORTED_TEXT_TIME_MS"))

    def test_restore_returns_visibility_lost_on_state_switching(self):
        # Регресс: переключение состояния вызывает setAllObjectsVisibility(False) и гасит уведомление
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        self.UI.setAllObjectsVisibility(False)
        self.assertFalse(notification.visible)
        manager.restore()
        self.assertTrue(notification.visible)

    def test_show_after_state_switching_shows_the_notification_again(self):
        # Регресс репорта: после паузы то же уведомление больше не показывалось
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        self.UI.setAllObjectsVisibility(False)
        manager.show(notification)
        self.assertTrue(notification.visible)
        self.assertEqual(self.UI.objects.count(notification), 1)

    def test_stale_timer_does_not_hide_the_notification_shown_again(self):
        # Регресс репорта: таймер прошлого показа снимал уведомление, показанное заново
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        firstTimer = self.UI.timers[0]
        self.UI.setAllObjectsVisibility(False)
        manager.show(notification)

        firstTimer[1](*firstTimer[2])  # сработал таймер первого показа
        self.assertIn(notification, self.UI.objects)
        self.assertTrue(notification.visible)

        self.UI.timers[-1][1](*self.UI.timers[-1][2])  # сработал таймер актуального показа
        self.assertNotIn(notification, self.UI.objects)

    def test_new_notification_replaces_the_previous_one(self):
        manager = self.createManager()
        first, second = self.create("first"), self.create("second")
        manager.show(first)
        firstTimer = self.UI.timers[0]
        manager.show(second)
        self.assertNotIn(first, self.UI.objects)
        self.assertIn(second, self.UI.objects)
        self.assertTrue(second.visible)

        firstTimer[1](*firstTimer[2])
        self.assertIn(second, self.UI.objects)

    def test_hide_removes_notification_and_makes_pending_timers_harmless(self):
        # Повторный запуск выкладывания: пользователь уже прочитал сообщение
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        staleTimer = self.UI.timers[0]
        manager.hide()
        self.assertNotIn(notification, self.UI.objects)

        manager.show(notification)
        staleTimer[1](*staleTimer[2])
        self.assertIn(notification, self.UI.objects)
        self.assertTrue(notification.visible)

    def test_restore_does_not_resurrect_notification_removed_by_timer(self):
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        self.UI.fireTimers()
        self.assertNotIn(notification, self.UI.objects)
        manager.restore()
        self.assertNotIn(notification, self.UI.objects)

    def test_notification_is_hidden_when_its_timer_fires(self):
        manager = self.createManager()
        notification = self.create()
        manager.show(notification)
        self.UI.fireTimers()
        self.assertNotIn(notification, self.UI.objects)


if __name__ == "__main__":
    unittest.main()