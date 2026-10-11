from typing import Any


class LinkableValue:
    val: float

    def __init__(self, val: float) -> None:
        self.val = val

    def __float__(self) -> float:
        return float(self.val)

    def __int__(self) -> int:
        return int(self.val)

    def __add__(self, other: "LinkableValue | float") -> float:
        if isinstance(other, LinkableValue):
            return self.val + other.val
        return self.val + other

    def __sub__(self, other: "LinkableValue | float") -> float:
        if isinstance(other, LinkableValue):
            return self.val - other.val
        return self.val - other

    def __mul__(self, other: "LinkableValue | float") -> float:
        if isinstance(other, LinkableValue):
            return self.val * other.val
        return self.val * other

    def __divmod__(self, other: "LinkableValue | float") -> float:
        if isinstance(other, LinkableValue):
            return self.val / other.val
        return self.val / other

    def __lt__(self, other: "LinkableValue | float") -> bool:
        if isinstance(other, LinkableValue):
            return self.val < other.val
        return self.val < other
    def __le__(self, other: "LinkableValue | float") -> bool:
        if isinstance(other, LinkableValue):
            return self.val <= other.val
        return self.val <= other
    def __gt__(self, other: "LinkableValue | float") -> bool:
        if isinstance(other, LinkableValue):
            return self.val > other.val
        return self.val > other
    def __ge__(self, other: "LinkableValue | float") -> bool:
        if isinstance(other, LinkableValue):
            return self.val >= other.val
        return self.val >= other
    def __repr__(self) -> str:
        return str(self.val)
    # def __st__(self):
    #     return str(self.val)


def editLinkableValue(oldVal: "LinkableValue | float", newVal: float) -> "LinkableValue | float":
    if isinstance(oldVal, LinkableValue):
        oldVal.val = newVal
        return oldVal
    return newVal


def linkableValueDumpsToJSON(obj: Any) -> float | None:
    if isinstance(obj, LinkableValue):
        return obj.val
