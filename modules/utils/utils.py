"""Utilities functions"""
import json


def load_json(filename: str):
    """Loads a json file"""
    with open(filename, encoding="utf-8", mode="r") as file:
        data = json.load(file)
    return data


def save_json(data: json, filename: str, should_be_sorted=True):
    """Saves a json file"""
    with open(filename, encoding="utf-8", mode="w") as file:
        json.dump(
            data,
            file,
            indent=4,
            sort_keys=should_be_sorted,
            separators=(',', ': '))


def convert_seconds_to_str(sec: float):
    """Returns a str representing a number of seconds"""
    msg = ""
    sec = round(sec)
    years = sec // 31536000
    if years != 0:
        msg += str(int(years)) + "y "
    sec -= years * 31536000
    days = sec // 86400
    if days != 0:
        msg += str(int(days)) + "d "
    sec -= days * 86400
    hours = sec // 3600
    if hours != 0:
        msg += str(int(hours)) + "h "
    sec -= hours * 3600
    minutes = sec // 60
    sec -= minutes * 60
    if minutes != 0:
        msg += str(int(minutes)) + "m "
    if sec != 0:
        msg += str(int(sec)) + "s "
    return msg[:-1]
