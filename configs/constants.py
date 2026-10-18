import logging
import os
import sys

import appdata

app_paths: appdata.AppDataPaths = appdata.AppDataPaths('.ThaumcraftAutoResearcher')

app_paths.setup()

# ------------------------
# UI and visual part
MARGIN: int = 20
FPS: int = 60


# ------------------------
# Files paths
def to_resource_path(relative_path: str) -> str:
    ''' Get absolute path to resource, works for dev and for PyInstaller '''
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base_path, relative_path)


def to_appdata_path(relative_path: str) -> str:
    ''' Get absolute path to file into appdata folder, cross-platform '''
    return os.path.join(str(app_paths.app_data_path), relative_path)


THAUM_VERSION_CONFIG_PATH: str = to_appdata_path('user_configs/thaumVersionConfig.json')
THAUM_CONTROLS_CONFIG_PATH: str = to_appdata_path('user_configs/thaumControlsConfig.json')
LANGUAGE_CONFIG_PATH: str = to_appdata_path('user_configs/language.json')
EDITION_CONFIG_PATH: str = to_appdata_path('user_configs/edition.json')
THAUM_ASPECT_RECIPES_CONFIG_PATH: str = to_resource_path('configs/aspects_configs/aspectsRecipes.json')
THAUM_ADDONS_ASPECT_RECIPES_CONFIG_PATH: str = to_resource_path('configs/aspects_configs/addonsAspectsRecipes.json')
THAUM_ASPECTS_ORDER_CONFIG_PATH: str = to_resource_path('configs/aspects_configs/aspectsOrder.json')


def getAspectImagePath(aspectName: str, colored: bool = True) -> str:
    return to_resource_path(f'images/{"color" if colored else "mono"}/{aspectName}.png')

UNKNOWN_ASPECT_IMAGE_PATH: str = to_resource_path('images/unknownAspect.png')
ASPECTS_IMAGES_SIZE: int = 32  # px

# ------------------------
# In-game inventory
# !!! Don't touch if you not sure !!!
INVENTORY_SLOTS_X: int = 9
INVENTORY_SLOTS_Y: int = 3

THAUM_ASPECTS_INVENTORY_SLOTS_X: int = 5
THAUM_ASPECTS_INVENTORY_SLOTS_Y: int = 5

THAUM_HEXAGONS_SLOTS_COUNT: int = 9  # must be odd

DELAY_BETWEEN_EVENTS: float = 0.15  # seconds
DELAY_BETWEEN_RENDER: float = 0.5  # seconds

# ------------------------
# Neurolink constants
FIELD_OBJECT_DETECTION_PATH: str = to_resource_path("models/field_object_detection.onnx")
INVENTORY_OBJECT_DETECTION_PATH: str = to_resource_path("models/inventory_object_detection.onnx")
FIELD_CLASS_NAMES_PATH: str = to_resource_path("models/field_class_names.txt")
INVENTORY_CLASS_NAMES_PATH: str = to_resource_path("models/inventory_class_names.txt")
NEUROLINK_FREE_HEXAGON_PREDICTION_NAME: str = "free_hex"
NEUROLINK_SCRIPT_IMAGE_PREDICTION_NAME: str = "script"
NEUROLINK_UNKNOWN_ASPECT_PREDICTION_NAME: str = "unknown"

# ------------------------
# Aspect link solves generation
MAX_SOLVE_RETRIES: int = 3
MAX_ASPECTS_SOLVING_PATH_LEN: int = 10

# ------------------------
# Other constants
IMAGES_TOLERANCE_PERCENT: float = 0.02
IMAGE_TMP_PATH: str = to_appdata_path('.tmp/tmp.png')
LOG_FILE_PATH: str = to_appdata_path('logs/logs.log')
LINK_GENERATION_MAX_TIME_MS: int = 1000 * 10  # 10 sec

# How long the message about aborted solving placing stays on the screen
SOLVING_ABORTED_TEXT_TIME_MS: int = 1000 * 20  # 20 sec

# ------------------------
# Inkwell (чернильница) tracking
# Клетки поля, которые игра перекрывает, когда в чернильнице закончились чернила:
# полоса в середине поля — весь ряд y=0 и клетки с нечётным x в ряду y=1
# (нечётные столбцы сдвинуты вниз на полклетки и тоже попадают под плашку).
# Пустой набор выключает отслеживание: решение работает как раньше.
INK_EXHAUSTED_MARKER_CELLS: set[tuple[int, int]] = {
    (-4, 0), (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
    (-3, 1), (-1, 1), (1, 1), (3, 1),
}
# Сколько маркерных клеток должно исчезнуть, чтобы считать чернила исчерпанными.
# При исчерпании пропадает вся полоса: на живых логах 11-12 из 11-13, то есть доля 0.92-1.0.
# В нормальном поле определение теряет 1-3 клетки (в том числе аспекты, которых бот не знает),
# поэтому одного порога на количество мало — нужна ещё доля от маркерных клеток, которые
# вообще есть на поле.
INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE: float = 0.8
# Нижний порог на количество: страховка от крошечной полосы (совсем маленькое поле)
INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT: int = 3
# Как часто перепроверять поле во время выкладывания: каждые N выложенных аспектов
INK_CHECK_EVERY_N_PLACED_ASPECTS: int = 3

# Loggers
MAX_LOG_FILE_SIZE_BYTES: int = 1024 * 1024 * 5  # 5 Mb
MAX_LOG_FILES_COUNT: int = 20
LOG_LEVEL: int = logging.DEBUG

# Donate urls
DONATE_URL_RUSSIA: str = 'https://tbank.ru/cf/82w1UbDljyM'
DONATE_CRYPTO_ID_GLOBAL: str = 'UQAYwm--Z4va2KK_Qk_e9GDhPxrTtnsWvzN6yQYPr2MiB1em'
# ------------------------
DEBUG: bool = True
# DEBUG = False

# PAINT_DEBUG = DEBUG
# PAINT_DEBUG = True
PAINT_DEBUG: bool = False
