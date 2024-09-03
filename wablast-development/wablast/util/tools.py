import random
import json
import re

from datetime import datetime
from os import path, makedirs

def get_datetime(format):
    timestamp = datetime.now()
    # '%d-%m-%Y %H:%M:%S'
    return timestamp.strftime(format)

class Folder:
    @staticmethod
    def mkdir(file_path):
        makedirs(path.dirname(file_path), exist_ok=True)

    @staticmethod
    def is_exists(file_path):
        return path.exists(path.expanduser(file_path))

def countdown(iterable, prefix = '', suffix = '', print_end = "\r"):
    def display_countdown(iteration):
        print(f'\r{prefix} {iteration}s {suffix}', end = print_end)

    # initial count down
    display_countdown(0)

    # update count down
    for i, item in enumerate(iterable):
        yield item
        display_countdown(item)

    # print new line on complete
    print()

def check_format_number(number):
    phone = str(number)
    phone = phone.strip('+')
    phone = phone.strip()
    phone = phone.split('.')[0]
    if phone[:2] == '62':
        return phone.strip()
    elif phone[:1] == '0':
        return f'62{phone[1:]}'
    elif phone[:1] == '8':
        return f'62{phone[:]}'
    else:
        return ''

def random_ua(k=1):
    # returns a random user agent from the latest user_agents.json file
    ua_pct = open('user_agents.json', 'r')
    ua = json.load(ua_pct)
    ua_pct.close()
    return random.choices(list(ua['ua'].values()), list(ua['pct'].values()), k=k)[0]

def sanitize_phone_number(phone):
    CHAR = [
        (r"\s", ""), # any whitespace character
        (r"\W*", "") # any non-alphanumeric character
    ]
    for old, new in CHAR:
        phone = re.sub(old, new, phone, flags=re.IGNORECASE)

    return phone

def reformat_chat_datetime(timestamp, character):
    for character in '[]':
        timestamp = timestamp.replace(character, '')

    timestamp_formated = timestamp.split(' ', 3)
    if len(timestamp_formated) > 3:
        timestamp_formated.pop(3)

    return ' '.join(timestamp_formated)
