from dataclasses import dataclass
from typing import cast
from typing import overload
from typing import Literal
from typing import Generic
from typing import TypeVar
from collections.abc import Callable

from pyperf._formatter import (format_number, format_seconds, format_filesize,
                               UNIT_FORMATTERS)


METADATA_VALUE_TYPES = (int, str, float)
MetadataValueType = int | str | float | list[str]
MetadataType = dict[str, MetadataValueType]
NUMBER_TYPES = (int, float)


def _common_metadata(metadatas: list[MetadataType]) -> MetadataType:
    if not metadatas:
        return {}

    metadata = dict(metadatas[0])
    for run_metadata in metadatas[1:]:
        for key in list(metadata):
            if metadata[key] != run_metadata.get(key,None):
                del metadata[key]
    return metadata


def format_generic(value: MetadataValueType) -> str:
    if not isinstance(value, str):
        return str(value)

    return value


def format_system_load(load: float) -> str:
    # Format system load read from /proc/loadavg on Linux (ex: 0.12)
    return '%.2f' % load


def is_strictly_positive(value: int) -> bool:
    return (value >= 1)


def is_positive(value: int | float) -> bool:
    return (value >= 0)


def is_tags(value: list[str]) -> bool:
    if not isinstance(value, list):
        return False
    return all(isinstance(x, str) and x not in ('all', '') for x in value)


def parse_load_avg(value: float | int | str) -> float | int:
    if isinstance(value, NUMBER_TYPES):
        return value
    else:
        # special case for load_avg_1min on pyperf < 0.7.2
        return float(value)


def format_noop(value: str) -> str:
    return value


# types: accepted types
T = TypeVar("T")

@dataclass(frozen=True)
class _MetadataInfo(Generic[T]):
    formatter: Callable[[T], str]
    types: tuple[type[T], ...]
    check_value: Callable[[T], bool] | None
    unit: str | None

BYTES = _MetadataInfo(format_filesize, (int,), is_positive, 'byte')
DATETIME = _MetadataInfo(format_noop, (str,), None, None)
LOOPS = _MetadataInfo(format_number, (int,), is_strictly_positive, 'integer')
WARMUPS = _MetadataInfo(format_number, (int,), is_positive, 'integer')
SECONDS = _MetadataInfo(format_seconds, NUMBER_TYPES, is_positive, 'second')
TAGS = _MetadataInfo(format_generic, (list,), is_tags, 'tag')
DEFAULT_METADATA_INFO: _MetadataInfo[MetadataValueType] = _MetadataInfo(format_generic, METADATA_VALUE_TYPES, None, None)

MetadataInfoType = (
    _MetadataInfo[float]
    | _MetadataInfo[int]
    | _MetadataInfo[list[str]]
    | _MetadataInfo[str]
    | _MetadataInfo[int | float]
    | _MetadataInfo[MetadataValueType]
)

# Registry of metadata keys
METADATA: dict[str, MetadataInfoType] = {
    'loops': LOOPS,
    'inner_loops': LOOPS,

    'duration': SECONDS,
    'uptime': SECONDS,
    'load_avg_1min': _MetadataInfo(format_system_load, NUMBER_TYPES, is_positive, None),

    'mem_max_rss': BYTES,
    'mem_peak_pagefile_usage': BYTES,
    'command_max_rss': BYTES,

    'unit': _MetadataInfo(format_noop, (str,), UNIT_FORMATTERS.__contains__, None),
    'date': DATETIME,
    'boot_time': DATETIME,

    'recalibrate_loops': LOOPS,
    'calibrate_warmups': WARMUPS,
    'recalibrate_warmups': WARMUPS,
    'tags': TAGS,
}

MetadataByteTypeName = Literal["mem_max_rss", "mem_peak_pagefile_usage", "command_max_rss"]
MetadataDatetimeTypeName = Literal["date", "boot_time"]
MetadataLoopTypeName = Literal["loops", "inner_loops", "recalibrate_loops"]
MetadataWarmupTypeName = Literal["calibrate_warmups", "recalibrate_warmups"]
MetadataNumberTypeName = Literal["duration", "uptime", "load_avg_1min"]
MetadataTagTypeName = Literal["tags"]
MetadataUnitTypeName = Literal["unit"]

MetadataIntTypeName = MetadataByteTypeName | MetadataLoopTypeName | MetadataWarmupTypeName
MetadataStringTypeName = MetadataDatetimeTypeName | MetadataUnitTypeName

@overload
def get_metadata_info(name: MetadataIntTypeName) -> _MetadataInfo[int]: ...

@overload
def get_metadata_info(name: MetadataNumberTypeName) -> _MetadataInfo[int | float]: ...

@overload
def get_metadata_info(name: MetadataStringTypeName) -> _MetadataInfo[str]: ...

@overload
def get_metadata_info(name: MetadataTagTypeName) -> _MetadataInfo[list[str]]: ...

@overload
def get_metadata_info(name: str) -> MetadataInfoType: ...

def get_metadata_info(name: str) -> MetadataInfoType:
    return METADATA.get(name, DEFAULT_METADATA_INFO)

def check_metadata(name: str, value: MetadataValueType) -> None:
    info = get_metadata_info(name)

    if not isinstance(name, str):
        raise TypeError("metadata name must be a string, got %s"
                        % type(name).__name__)

    if not isinstance(value, info.types):
        raise ValueError("invalid metadata %r value type: got %r"
                         % (name, type(value).__name__))

    if info.check_value is not None:
        checker = cast(Callable[[MetadataValueType], bool], info.check_value)
        if not checker(value):
            raise ValueError("invalid metadata %r value: %r"
                            % (name, value))


def parse_metadata(metadata: MetadataType) -> MetadataType:
    result = {}
    for name, value in metadata.items():
        if isinstance(value, str):
            value = value.strip()
            if '\n' in value or '\r' in value:
                raise ValueError("newline characters are not allowed "
                                 "in metadata values: %r" % value)
            if not value:
                raise ValueError("metadata %r value is empty" % name)
        check_metadata(name, value)
        result[name] = value
    return result


def format_metadata(name: str, value: MetadataValueType) -> str:
    info = get_metadata_info(name)
    formatter = cast(Callable[[MetadataValueType], str], info.formatter)
    return formatter(value)


class Metadata:
    def __init__(self, name: str, value: MetadataValueType):
        self._name = name
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> MetadataValueType:
        return self._value

    def __str__(self) -> str:
        info = get_metadata_info(self._name)
        formatter = cast(Callable[[MetadataValueType], str], info.formatter)
        return formatter(self._value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Metadata):
            return False
        return (self._name == other._name and self._value == other._value)

    def __repr__(self) -> str:
        return ('<pyperf.Metadata name=%r value=%r>'
                % (self._name, self._value))


def _exclude_common_metadata(metadata: MetadataType, common_metadata: MetadataType) -> MetadataType:
    if common_metadata:
        metadata = {key: value for key, value in metadata.items()
                    if key not in common_metadata}
    return metadata
