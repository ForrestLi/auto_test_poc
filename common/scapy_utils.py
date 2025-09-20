from scapy.all import *
from typing import Optional, Union


class StrFixedLenField(StrFixedLenField):
    """Handle ASCII string encoding/decoding automatically."""

    def i2m(self, pkt, x: Optional[str]) -> bytes:
        return x.encode("ascii") if x is not None else b""

    def m2i(self, pkt, x: bytes) -> str:
        return x.decode("ascii")

    def any2i(self, pkt, x: Union[str, bytes]) -> str:
        if isinstance(x, str):
            return x
        if isinstance(x, bytes):
            return x.decode("ascii")
        raise ValueError(f"Expected str or bytes, got {type(x).__name__}")


class PaddedStrFixedLenFieldBase(StrFixedLenField):
    """Base class for padded string fields."""

    __slots__ = ["padding", "undefined_value"]

    def __init__(
        self,
        name,
        default,
        length=None,
        length_from=None,
        padding=" ",
        undefined_value="",
    ):
        super().__init__(name, default, length=length, length_from=length_from)
        self.padding = str(padding)
        self.undefined_value = str(undefined_value)


class RPaddedStrFixedLenField(PaddedStrFixedLenFieldBase):
    """Right-padded fixed-length ASCII string field."""

    def i2m(self, pkt, x: Optional[str]) -> bytes:
        if x is None:
            x = self.undefined_value
        length = self.length_from(pkt)
        padded = x.ljust(length, self.padding)[:length]
        return super().i2m(pkt, padded)

    def m2i(self, pkt, s: bytes) -> Optional[str]:
        decoded = super().m2i(pkt, s)
        stripped = decoded.rstrip(self.padding)
        return None if stripped == self.undefined_value else stripped


class LPaddedStrFixedLenField(PaddedStrFixedLenFieldBase):
    """Left-padded fixed-length ASCII string field."""

    def i2m(self, pkt, x: Optional[str]) -> bytes:
        if x is None:
            x = self.undefined_value
        length = self.length_from(pkt)
        padded = x.rjust(length, self.padding)[:length]
        return super().i2m(pkt, padded)

    def m2i(self, pkt, s: bytes) -> Optional[str]:
        decoded = super().m2i(pkt, s)
        stripped = decoded.lstrip(self.padding)
        return None if stripped == self.undefined_value else stripped


class LPaddedAsciiIntFixedLenField(LPaddedStrFixedLenField):
    """Left-padded fixed-length ASCII integer field."""

    def i2m(self, pkt, x: Optional[int]) -> bytes:
        return super().i2m(pkt, str(x) if x is not None else None)

    def m2i(self, pkt, s: bytes) -> Optional[int]:
        value = super().m2i(pkt, s)
        return int(value) if value is not None else None

    def any2i(self, pkt, x: Union[int, str, bytes]) -> Optional[int]:
        if x is None:
            return None
        if isinstance(x, int):
            return x
        return int(super().any2i(pkt, x))
