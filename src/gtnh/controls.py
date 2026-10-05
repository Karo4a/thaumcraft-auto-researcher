import logging

from configs.constants import to_appdata_path
from utils.AppState import readJSONConfig, saveJSONConfig

GTNH_THAUM_CONTROLS_CONFIG_PATH = to_appdata_path('user_configs/gtnhThaumControlsConfig.json')


def readGtnhThaumWindowControls(path: str | None = None) -> dict | None:
    return readJSONConfig(path or GTNH_THAUM_CONTROLS_CONFIG_PATH)


def saveGtnhThaumWindowControls(pointWritingMaterials, pointPapers,
                                rectAspectsListingLT, rectAspectsListingRB,
                                rectAspectsListingLT2, rectAspectsListingRB2,
                                rectInventoryLT, rectInventoryRB, rectHexagonsCC,
                                hexagonSlotSizeY, path: str | None = None):
    saveJSONConfig(path or GTNH_THAUM_CONTROLS_CONFIG_PATH, {
        "pointWritingMaterials": {"x": pointWritingMaterials.x, "y": pointWritingMaterials.y},
        "pointPapers": {"x": pointPapers.x, "y": pointPapers.y},
        "rectAspectsListingLT": {"x": rectAspectsListingLT.x, "y": rectAspectsListingLT.y},
        "rectAspectsListingRB": {"x": rectAspectsListingRB.x, "y": rectAspectsListingRB.y},
        "rectAspectsListingLT2": {"x": rectAspectsListingLT2.x, "y": rectAspectsListingLT2.y},
        "rectAspectsListingRB2": {"x": rectAspectsListingRB2.x, "y": rectAspectsListingRB2.y},
        "rectInventoryLT": {"x": rectInventoryLT.x, "y": rectInventoryLT.y},
        "rectInventoryRB": {"x": rectInventoryRB.x, "y": rectInventoryRB.y},
        "rectHexagonsCC": {"x": rectHexagonsCC.x, "y": rectHexagonsCC.y},
        "hexagonSlotSizeY": hexagonSlotSizeY,
    })
    logging.info("Thaum window controls config successfully saved (GTNH)")
