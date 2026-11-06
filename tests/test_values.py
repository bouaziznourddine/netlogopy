"""Python ⇄ NetLogo value conversion."""
import math

import pytest

import netlogopy.netlogopy as nlp
from netlogopy.netlogopy import list2nllist


def test_list2nllist_numbers_strings_booleans():
    assert list2nllist([1, 2.5, "car", True, False]) == '[1 2.5 "car" true false]'


def test_list2nllist_escapes_quotes_backslashes_and_newlines():
    text = list2nllist(['say "hi"', "C:\\data\\img.png", "a\nb", "tab\there"])
    assert text == r'["say \"hi\"" "C:\\data\\img.png" "a\nb" "tab\there"]'


def test_list2nllist_nested_lists_and_tuples():
    assert list2nllist([[1, 2], (3, 4), []]) == "[[1 2] [3 4] []]"


def test_list2nllist_rejects_nan_and_infinity():
    with pytest.raises(ValueError):
        list2nllist([math.nan])
    with pytest.raises(ValueError):
        list2nllist([math.inf])


def test_list2nllist_numpy_scalars():
    np = pytest.importorskip("numpy")
    assert list2nllist([np.int64(3), np.float64(2.5)]) == "[3 2.5]"


@pytest.mark.parametrize("text, expected", [
    ("20.0", 20.0),
    ("-3.5", -3.5),
    ("1.0E-5", 1e-5),
    ("true", True),
    ("false", False),
    ("car", "car"),
    ("", ""),
    ("[]", []),
    ("[20.0, 5.5]", [20.0, 5.5]),
    ("[[0.0, 1.0, 2.0], [1.0, 3.5, 4.5]]", [[0.0, 1.0, 2.0], [1.0, 3.5, 4.5]]),
    ("[car, default]", ["car", "default"]),
    ("[hello world]", ["hello world"]),           # one string with a space
    ("[1 2 3]", [1.0, 2.0, 3.0]),                 # NetLogo's own list format
    ('["a" "b c"]', ["a", "b c"]),
    ("[[1 2] [3 4]]", [[1.0, 2.0], [3.0, 4.0]]),
    ("[3.0]", [3.0]),
    ("(turtle 0)", "(turtle 0)"),
    ("nan", "nan"),                               # text, not a number
])
def test_parse_nl_value(text, expected):
    assert nlp._parse_nl_value(text) == expected


def test_parse_nl_value_keeps_non_text_results():
    assert nlp._parse_nl_value(3.0) == 3.0
    assert nlp._parse_nl_value([1, 2]) == [1, 2]


def test_parse_error_message_is_returned_as_text():
    message = "OF expected input to be a turtle agentset or turtle but got NOBODY instead."
    assert nlp._parse_nl_value(message) == message
