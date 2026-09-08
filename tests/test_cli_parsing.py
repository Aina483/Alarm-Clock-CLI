import argparse
import pytest

from alarm_clock.cli import parse_time


def test_parses_valid_time():
    assert parse_time("07:30") == "07:30"


def test_normalizes_single_digit_hour():
    assert parse_time("7:30") == "07:30"


def test_accepts_midnight_and_end_of_day():
    assert parse_time("00:00") == "00:00"
    assert parse_time("23:59") == "23:59"


@pytest.mark.parametrize("bad", ["24:00", "12:60", "noon", "7-30", "7:3"])
def test_rejects_invalid_time(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_time(bad)
