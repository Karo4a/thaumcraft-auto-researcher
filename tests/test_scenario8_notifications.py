"""Регрессы уведомлений сценария 8: они должны переживать любые переключения состояний.

Баг репорта: пауза (и любое другое переключение состояния) гасит все объекты сцены
(setAllObjectsVisibility(False)), addObject не возвращает объекту видимость, поэтому
после паузы не показывалось ни одно новое уведомление. Второй баг — таймер прошлого показа
снимал уведомление, показанное заново.
"""
import os
import sys
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from test_scenario8_ink import (  # noqa: E402
    FakeUI, FakeTI, fieldDetection, SOLVE, makeTranslations,
    PLACE_BUTTON_TEXT, INK_TEXT_KEY, ABORTED_TEXT_KEY,
)
from configs.translations import TEXTS  # noqa: E402
from controllers.Scenarios import scenario8_Researchings as scenario  # noqa: E402
from controllers.Scenarios.shared import NotificationManager  # noqa: E402
from UI.OverlayUI import KeyboardKeys  # noqa: E402
from UI.primitives.Circle import Circle  # noqa: E402
from utils import AppState  # noqa: E402


class NotEnoughAspectsTI(FakeTI):
    """Выкладывание обрывается так же, как при нехватке аспектов в инвентаре."""

    def fillByLinkMap(self, aspectsMap, onAspectPlaced=None):
        for coords in sorted(aspectsMap)[:2]:
            self.placed.append(coords)
            if onAspectPlaced is not None and not onAspectPlaced():
                return False
        return False


class Scenario8NotificationsTest(unittest.TestCase):
    def setUp(self):
        self.originalTranslatedTexts = AppState.translatedTexts
        self.originalCheckEvery = scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS
        self.originalGenerateLinkMap = scenario.generateLinkMap
        self.originalRenderDelay = scenario.renderDelay
        self.originalEventsDelay = scenario.eventsDelay
        AppState.translatedTexts = makeTranslations()
        scenario.generateLinkMap = lambda *args, **kwargs: dict(SOLVE)
        scenario.renderDelay = lambda: None
        scenario.eventsDelay = lambda: None

    def tearDown(self):
        AppState.translatedTexts = self.originalTranslatedTexts
        scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS = self.originalCheckEvery
        scenario.generateLinkMap = self.originalGenerateLinkMap
        scenario.renderDelay = self.originalRenderDelay
        scenario.eventsDelay = self.originalEventsDelay

    # --- Вспомогательное

    def startScenario(self, ti):
        UI = FakeUI()
        scenario.runResearching(UI, ti)
        return UI

    def joinThreads(self):
        for thread in threading.enumerate():
            if thread is not threading.current_thread():
                thread.join(timeout=10)

    def clickButton(self, UI, text):
        # Объекты всех диалогов лежат в UI.objects сразу, поэтому нажимаем на видимую кнопку
        buttons = [obj for obj in UI.objects if getattr(obj, "text", None) == text and obj.visible]
        self.assertEqual(len(buttons), 1, f"видимая кнопка «{text}» не найдена")
        buttons[0].onClickCallback(*buttons[0].onClickCallbackArgs)
        self.joinThreads()

    def clickPlaceSolving(self, UI):
        self.clickButton(UI, PLACE_BUTTON_TEXT)

    def pressPauseHotkey(self, UI):
        """Ctrl+Shift+Space: в active он ставит паузу, в паузе возвращает в active."""
        hotkeys = [callback for keys, callback in UI.keyCallbacks if len(keys) == 3]
        self.assertEqual(len(hotkeys), 1, "хоткей паузы не найден")
        hotkeys[0]()

    def notifications(self, UI, textKey):
        return [obj for obj in UI.objects if getattr(obj, "text", None) == textKey]

    def visibleNotifications(self, UI, textKey):
        return [obj for obj in self.notifications(UI, textKey) if obj.visible]

    def assertNotificationVisible(self, UI, textKey, message=""):
        self.assertEqual(len(self.notifications(UI, textKey)), 1, f"уведомление потерялось: {message}")
        self.assertEqual(len(self.visibleNotifications(UI, textKey)), 1, f"уведомление не видно: {message}")

    def assertNotificationGone(self, UI, textKey, message=""):
        self.assertEqual(self.visibleNotifications(UI, textKey), [], f"уведомление всё ещё видно: {message}")

    def notificationTimers(self, UI):
        """Таймеры снятия уведомлений (таймеры решения регистрируются так же, но с другим колбэком)."""
        return [timer for timer in UI.timedEvents
                if getattr(timer[1], "__func__", None) is NotificationManager._hideIfShown]

    def fireTimer(self, timer):
        timer[1](*timer[2])

    # --- Переходы состояний

    def test_ink_notification_survives_pause_and_resume(self):
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после отказа выкладывать")

        self.pressPauseHotkey(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "в паузе")

        self.pressPauseHotkey(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после возврата в active")

    def test_abort_notification_is_visible_again_after_pause(self):
        # Основной регресс репорта: после паузы уведомление об аборте больше не показывалось
        ti = NotEnoughAspectsTI([fieldDetection()], SOLVE)
        UI = self.startScenario(ti)
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, ABORTED_TEXT_KEY, "после первого аборта")

        self.pressPauseHotkey(UI)
        self.pressPauseHotkey(UI)
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, ABORTED_TEXT_KEY, "после повторного аборта")

    def test_notification_survives_cell_settings_state(self):
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "до входа в настройки клетки")

        cells = [obj for obj in UI.objects if isinstance(obj, Circle)]
        self.assertTrue(cells, "клетки поля не найдены")
        cells[0].onClickCallback(*cells[0].onClickCallbackArgs)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "в состоянии настроек клетки")

        escCallbacks = [callback for keys, callback in UI.keyCallbacks if tuple(keys) == (KeyboardKeys.esc,)]
        self.assertEqual(len(escCallbacks), 1, "клавиша выхода из настроек клетки не найдена")
        escCallbacks[0]()
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после выхода из настроек клетки")

    def test_notification_survives_multy_researches_and_donate_dialogues(self):
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)

        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.automaticMode])
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "в диалоге авто-режима")
        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.back])

        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.goToDonate])
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "в диалоге donate")
        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.back])
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после возврата из donate")

    def test_notification_survives_regenerate_solving(self):
        # Перегенерация гасит всю сцену (объекты, диалоги, курсор) — уведомление должно вернуться
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "до перегенерации")

        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.regenerateSolving])
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после перегенерации решения")

    def test_new_placing_attempt_resets_the_visible_notification(self):
        # Пользователь нажал «Выложить решение» — сообщение прочитано, экран чистый для скриншотов
        ti = FakeTI([fieldDetection(inkExhausted=True)], SOLVE)
        UI = self.startScenario(ti)
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после отказа из-за пустой чернильницы")

        ti.detections = [fieldDetection()]  # чернильницу пополнили
        self.clickPlaceSolving(UI)
        self.assertEqual(ti.papersTakenOut, 1, "выкладывание не прошло")
        self.assertNotificationGone(UI, INK_TEXT_KEY, "после нового выкладывания")
        self.assertEqual(self.notifications(UI, INK_TEXT_KEY), [], "уведомление осталось в сцене")

    # --- Время показа

    def test_notification_is_removed_when_its_display_time_is_over(self):
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)
        timers = self.notificationTimers(UI)
        self.assertEqual(len(timers), 1, "таймер показа уведомления не зарегистрирован")

        self.fireTimer(timers[0])
        self.assertEqual(self.notifications(UI, INK_TEXT_KEY), [], "уведомление не убрано по таймеру")

    def test_stale_timer_does_not_hide_the_notification_shown_again(self):
        # Регресс репорта: таймер прошлого показа снимал уведомление, показанное заново
        UI = self.startScenario(FakeTI([fieldDetection(inkExhausted=True)], SOLVE))
        self.clickPlaceSolving(UI)
        firstTimer = self.notificationTimers(UI)[0]

        self.pressPauseHotkey(UI)
        self.pressPauseHotkey(UI)
        self.clickPlaceSolving(UI)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после повторного показа")

        self.fireTimer(firstTimer)
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после срабатывания старого таймера")

    def test_ink_notification_is_shown_in_automatic_mode(self):
        # Чернила кончились посреди автоматического прогона: сообщение показывается как раньше
        scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS = 1
        ti = FakeTI([fieldDetection(inkExhausted=False), fieldDetection(inkExhausted=True)], SOLVE)
        UI = self.startScenario(ti)
        self.clickButton(UI, AppState.translatedTexts[TEXTS.Buttons.automaticMode])
        self.clickButton(UI, "3")
        self.assertNotificationVisible(UI, INK_TEXT_KEY, "после авто-прогона с пустой чернильницей")


if __name__ == "__main__":
    unittest.main()