import datetime
import re
import math
from typing import Callable, Any, Sequence
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.core.described_as import DescribedAs
from hamcrest.core.helpers.wrap_matcher import wrap_matcher
from hamcrest import *


class Converted(BaseMatcher):
    def __init__(
        self, convert: Callable, matcher: BaseMatcher, description: str = ""
    ) -> None:
        self.convert = convert
        self.matcher = wrap_matcher(matcher)
        self.description = description

    def matches(self, item: Any, mismatch_description: Any = None) -> bool:
        return self.matcher.matches(self.convert(item))

    def describe_to(self, description: Any) -> None:
        self.matcher.describe_to(description)
        description.append_text(self.description)


def converted(
    convert: Callable, matcher: BaseMatcher, description: str = ""
) -> Converted:
    """Matches if `matcher` matches after passed through `convert`."""
    return Converted(convert, matcher, description)


class IsCloseToDateTime(BaseMatcher):
    def __init__(self, value: datetime.datetime, delta: datetime.timedelta) -> None:
        if not isinstance(value, datetime.datetime):
            raise TypeError("IsCloseToDateTime value must be datetime")
        if not isinstance(delta, datetime.timedelta):
            raise TypeError("IsCloseToDateTime delta must be timedelta")
        self.value = value
        self.delta = delta

    def matches(self, item: Any, mismatch_description: Any = None) -> bool:
        if not isinstance(item, datetime.datetime):
            return False
        return abs((item - self.value).total_seconds()) <= self.delta.total_seconds()

    def describe_mismatch(self, item: Any, mismatch_description: Any) -> None:
        if not isinstance(item, datetime.datetime):
            super().describe_mismatch(item, mismatch_description)
        else:
            actual_delta = abs(item - self.value)
            mismatch_description.append_description_of(item).append_text(
                " differed by "
            ).append_description_of(actual_delta)

    def describe_to(self, description: Any) -> None:
        description.append_text("a datetime value within ").append_description_of(
            self.delta
        ).append_text(" of ").append_description_of(self.value)


def close_to_datetime(
    value: datetime.datetime, delta: datetime.timedelta
) -> IsCloseToDateTime:
    """Matches if object is a datetime close to given value within a timedelta."""
    return IsCloseToDateTime(value, delta)


def fix_close_to_datetime(
    value: datetime.datetime, delta: datetime.timedelta
) -> Converted:
    """Matches if object is a FIX timestamp close to a given datetime value."""
    return converted(
        fromFixTimeStamp, close_to_datetime(value, delta), " as fix datetime"
    )


ARG_PATTERN = re.compile(r"%(\d+)")


class AppendDescription(BaseMatcher):
    def __init__(
        self, description_template: str, matcher: BaseMatcher, *values: Any
    ) -> None:
        self.template = description_template
        self.matcher = wrap_matcher(matcher)
        self.values = values

    def matches(self, item: Any, mismatch_description: Any = None) -> bool:
        return self.matcher.matches(item)

    def describe_mismatch(self, item: Any, mismatch_description: Any) -> None:
        self.matcher.describe_mismatch(item, mismatch_description)
        parts = []
        last_pos = 0
        for match in ARG_PATTERN.finditer(self.template):
            parts.append(self.template[last_pos : match.start()])
            arg_index = int(match.group(1))
            parts.append(str(self.values[arg_index]))
            last_pos = match.end()
        parts.append(self.template[last_pos:])
        mismatch_description.append_text("".join(parts))

    def describe_to(self, description: Any) -> None:
        self.matcher.describe_to(description)


def append_description(
    matcher: BaseMatcher, description: str, *values: Any
) -> AppendDescription:
    """Appends custom failure description to a given matcher's description."""
    return AppendDescription(description, matcher, *values)
