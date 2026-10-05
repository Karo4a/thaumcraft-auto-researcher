import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in (_ROOT_DIR, _SRC_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from controllers import Scenarios
from UI.OverlayUI import OverlayUI
from configs.constants import LOG_FILE_PATH, MAX_LOG_FILE_SIZE_BYTES, DEBUG, LOG_LEVEL, MAX_LOG_FILES_COUNT
from editions import getEditionNames
from utils import AppState
from utils.utils import createDirByFilePath

createDirByFilePath(LOG_FILE_PATH)
loggingHandlers = [logging.handlers.RotatingFileHandler(filename=LOG_FILE_PATH, maxBytes=MAX_LOG_FILE_SIZE_BYTES, backupCount=MAX_LOG_FILES_COUNT)]
if DEBUG:
    loggingHandlers.append(logging.StreamHandler(sys.stdout))  # output both to console and log-files
logging.basicConfig(
    handlers=loggingHandlers,
    format="%(asctime)s [%(levelname)s] (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
    level=LOG_LEVEL,
    force=True,
)

UI = OverlayUI(opacity=1)


def parseArgs():
    parser = argparse.ArgumentParser(description="Thaumcraft Auto Researcher")
    parser.add_argument("--edition", choices=getEditionNames(), default=None,
                        help="Game edition to use for this session (overrides saved config)")
    return parser.parse_args()


def main(args):
    try:
        AppState.rereadLanguage()
        AppState.rereadEdition()
        editionName = args.edition or AppState.selectedEdition
        if editionName is None:
            Scenarios.chooseEdition(UI)
            return None

        Scenarios.activateEdition(editionName)
        AppState.selectedEdition = editionName
        Scenarios.routeStartup(UI)
        return None
    except Exception as e:
        logging.critical(f"Error excepted in main thread: {e}")
        return None


if __name__ == '__main__':
    logging.info("Program started")
    logging.info("###############")
    try:
        args = parseArgs()
    except SystemExit as error:
        sys.exit(error.code)
    except Exception as e:
        logging.critical(f"Error while parsing command line arguments: {e}")
        sys.exit(2)
    try:
        UI.start(lambda: main(args))
    except Exception as e:
        logging.critical(f"Error excepted in UI thread: {e}")
