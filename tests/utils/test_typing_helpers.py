from src.utils import typing_helpers


def test_is_str():
    assert typing_helpers.is_str("hello") is True
    assert typing_helpers.is_str(123) is False


def test_is_non_empty_str():
    assert typing_helpers.is_non_empty_str(" oi ") is True
    assert typing_helpers.is_non_empty_str("   ") is False
    assert typing_helpers.is_non_empty_str(0) is False


def test_is_str_dict():
    assert typing_helpers.is_str_dict({"a": "1"}) is True
    assert typing_helpers.is_str_dict({"a": 1}) is False
    assert typing_helpers.is_str_dict(123) is False


def test_is_str_iterable_accepts_iterables_of_str():
    assert typing_helpers.is_str_iterable(["x", "y"]) is True

    def gen():
        yield "a"
        yield "b"

    assert typing_helpers.is_str_iterable(gen()) is True


def test_is_str_iterable_rejects_non_str_or_non_iterable():
    assert typing_helpers.is_str_iterable([1, "b"]) is False
    assert typing_helpers.is_str_iterable(object()) is False


def test_is_optional_str():
    assert typing_helpers.is_optional_str("x") is True
    assert typing_helpers.is_optional_str(None) is True
    assert typing_helpers.is_optional_str(10) is False
