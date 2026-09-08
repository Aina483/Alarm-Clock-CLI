import argparse

import pytest

from alarm_clock.cli import (
    parse_time,
    positive_float,
    positive_int,
    build_parser,
)


def test_parses_valid_time():
    assert parse_time("07:30") == "07:30"


def test_normalizes_single_digit_hour():
    assert parse_time("7:30") == "07:30"


def test_accepts_midnight_and_end_of_day():
    assert parse_time("00:00") == "00:00"
    assert parse_time("23:59") == "23:59"


@pytest.mark.parametrize(
    "bad",
    ["24:00", "12:60", "noon", "7-30", "7:3"],
)
def test_rejects_invalid_time(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_time(bad)



def test_positive_snooze_value():
    assert positive_int("5") == 5



@pytest.mark.parametrize("bad", ["0", "-1", "abc"])
def test_rejects_invalid_snooze_value(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int(bad)



def test_positive_interval_value():
    assert positive_float("0.5") == 0.5
    assert positive_float("1") == 1.0



@pytest.mark.parametrize("bad", ["0", "-1", "abc"])
def test_rejects_invalid_interval_value(bad):
    with pytest.raises(argparse.ArgumentTypeError):
        positive_float(bad)



def test_list_supports_all_flag():
    parser = build_parser()

    args = parser.parse_args(
        ["list", "--all"]
    )

    assert args.command == "list"
    assert args.all is True



def test_list_defaults_to_enabled_only():
    parser = build_parser()

    args = parser.parse_args(["list"])

    assert args.all is False



def test_run_supports_custom_interval():
    parser = build_parser()

    args = parser.parse_args(
        ["run", "--interval", "2.5"]
    )

    assert args.command == "run"
    assert args.interval == 2.5



def test_run_defaults_to_one_second():
    parser = build_parser()

    args = parser.parse_args(["run"])

    assert args.interval == 1.0



def test_repeat_modes_are_validated():
    parser = build_parser()

    for repeat in (
        "once",
        "daily",
        "weekdays",
        "weekends",
    ):
        args = parser.parse_args(
            ["add", "07:00", "--repeat", repeat]
        )

        assert args.repeat == repeat