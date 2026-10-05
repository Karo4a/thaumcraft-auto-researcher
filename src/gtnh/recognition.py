from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logic.onnx_inference import ObjectPrediction


def is_digit(prediction: "ObjectPrediction") -> bool:
    return prediction.predictionName in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


def is_aspect(prediction: "ObjectPrediction") -> bool:
    return not is_digit(prediction)


def prediction_inside_prediction(pred_inner: Any, pred_outer: Any) -> bool:
    """True, если pred_inner находится внутри pred_outer"""
    x_min = pred_outer.x - pred_outer.width // 2
    x_max = pred_outer.x + pred_outer.width // 2
    y_min = pred_outer.y - pred_outer.height // 2
    y_max = pred_outer.y + pred_outer.height // 2
    return x_min <= pred_inner.x <= x_max and y_min <= pred_inner.y <= y_max


# Слияние кластеров якорное (prev_x не обновляется при замене result[-1]) — это осознанный
# parity-порт master: аспекты-дубли могут остаться, но поведение совпадает с GTNH-веткой.
def remove_same_spot_predictions(digit_predictions: list) -> list:
    """
    Для случаев, когда на одну цифру приходится несколько предсказаний, расположенных примерно в одном месте.
    Убирает лишние предсказания, оставляя только самые уверенные
    """
    MIN_VALID_DIFF = 2.0
    prev_x = -666
    result = []
    digit_predictions.sort(key=lambda pred: pred.x)
    for digit_pred in digit_predictions:
        if abs(prev_x - digit_pred.x) < MIN_VALID_DIFF:
            if digit_pred.confidence > result[-1].confidence:
                result[-1] = digit_pred
        else:
            result.append(digit_pred)
            prev_x = digit_pred.x
    return result


def splitAspectsAndDigits(predictions: list) -> tuple[list, list]:
    aspects = []
    digits = []
    for prediction in predictions:
        if is_digit(prediction):
            digits.append(prediction)
        else:
            aspects.append(prediction)
    return aspects, digits


def filterByMaxConfidence(predictions: list) -> list:
    filteredAspects = {}
    for prediction in predictions:
        aspect = filteredAspects.get(prediction.predictionName)
        if aspect is None or prediction.confidence > aspect.confidence:
            filteredAspects[prediction.predictionName] = prediction
    return list(filteredAspects.values())


def group_aspects_and_digits(predictionsAspect: list, predictionsDigit: list) -> list[tuple]:
    result = []
    for aspect_pred in predictionsAspect:
        aspect_digits = []
        for digit_pred in predictionsDigit:
            if prediction_inside_prediction(digit_pred, aspect_pred):
                aspect_digits.append(digit_pred)
        result.append((aspect_pred, aspect_digits))
    return result


def aspects_count(predictionsAspect: list, predictionsDigit: list) -> dict[str, int]:
    """
    Каждому аспекту подставляет его распознанное количество.
    Вызывать после filterByMaxConfidence: дубли одного аспекта перезаписываются (последний побеждает).
    """
    counts = dict()
    for aspect_pred, aspect_digits_pred in group_aspects_and_digits(predictionsAspect, predictionsDigit):
        aspect_digits_pred = remove_same_spot_predictions(aspect_digits_pred)
        aspect_digits_pred.sort(key=lambda pred: pred.x)
        number = 0
        for digit_pred in aspect_digits_pred:
            number *= 10
            number += int(digit_pred.predictionName)
        counts[aspect_pred.predictionName] = number
    return counts
