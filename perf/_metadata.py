from __future__ import division, print_function, absolute_import

import collections
import six

from perf import _format_number, _format_seconds, _format_filesize, _UNIT_FORMATTERS


_METADATA_VALUE_TYPES = six.integer_types + six.string_types + (float,)
NUMBER_TYPES = six.integer_types + (float,)

# Registry of metadata keys
_MetadataInfo = collections.namedtuple('_MetadataInfo', 'formatter types check_value unit')


def _common_metadata(metadatas):
    if not metadatas:
        return dict()

    metadata = dict(metadatas[0])
    for run_metadata in metadatas[1:]:
        for key in set(metadata) - set(run_metadata):
            del metadata[key]
        for key in set(run_metadata) & set(metadata):
            if run_metadata[key] != metadata[key]:
                del metadata[key]
    return metadata


def _format_metadata(value):
    if not isinstance(value, six.string_types):
        return str(value)

    return value


def _format_system_load(load):
    # Formatter for system load read from /proc/loadavg on Linux (ex: 0.12)
    if isinstance(load, (int, float)):
        return '%.2f' % load
    else:
        # backward compatibility with perf 0.7.0 (load stored as string)
        return load


def _is_strictly_positive(value):
    return (value >= 1)


def _is_positive(value):
    # special case for load_avg_1min on perf < 0.7.2
    if isinstance(value, six.string_types):
        return True

    return (value >= 0)


def _format_noop(value):
    return value


_METADATA = {
    'loops': _MetadataInfo(_format_number, six.integer_types, _is_strictly_positive, 'integer'),
    'inner_loops': _MetadataInfo(_format_number, six.integer_types, _is_strictly_positive, 'integer'),

    'duration': _MetadataInfo(_format_seconds, NUMBER_TYPES, _is_positive, 'second'),
    'load_avg_1min': _MetadataInfo(_format_system_load, six.string_types + NUMBER_TYPES, _is_positive, None),

    'mem_max_rss': _MetadataInfo(_format_filesize, six.integer_types, _is_strictly_positive, 'byte'),
    'unit': _MetadataInfo(_format_noop, six.string_types, _UNIT_FORMATTERS.__contains__, None),
}

_DEFAULT_METADATA_INFO = _MetadataInfo(_format_metadata, _METADATA_VALUE_TYPES, None, None)


def _check_metadata(name, value):
    info = _METADATA.get(name, _DEFAULT_METADATA_INFO)

    if not isinstance(name, six.string_types):
        raise TypeError("metadata name must be a string, got %s"
                        % type(name).__name__)

    if not isinstance(value, info.types):
        raise ValueError("invalid metadata %r value type: got %r"
                        % (name, type(value).__name__))

    if info.check_value is not None and not info.check_value(value):
        raise ValueError("invalid metadata %r value: %r"
                        % (name, value))


def parse_metadata(metadata):
    result = {}
    for name, value in metadata.items():
        _check_metadata(name, value)
        if isinstance(value, six.string_types):
            if '\n' in value or '\r' in value:
                raise ValueError("newline characters are not allowed "
                                 "in metadata values: %r" % value)
            value = value.strip()
            if not value:
                raise ValueError("metadata %r value is empty" % name)
        result[name] = value
    return result


class Metadata(object):
    def __init__(self, name, value):
        self._name = name
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __str__(self):
        info = _METADATA.get(self._name, _DEFAULT_METADATA_INFO)
        return info.formatter(self._value)

    def __eq__(self, other):
        if not isinstance(other, Metadata):
            return False
        return (self._name == other._name and self._value == other._value)

    if six.PY2:
        def __ne__(self, other):
            # negate __eq__()
            return not(self == other)

    def __repr__(self):
        return ('<perf.Metadata name=%r value=%r>'
                % (self._name, self._value))
