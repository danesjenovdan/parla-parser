from .utils import fix_name, name_parser

from ..settings import API_URL, API_AUTH

from requests.auth import HTTPBasicAuth

import requests
import editdistance

from datetime import datetime

import logging
logger = logging.getLogger('base logger')

class BaseParser(object):
    def __init__(self, reference):
        self.reference = reference
        self.storage = reference.storage

    def remove_leading_zeros(self, word, separeted_by=[',', '-', '/']):
        for separator in separeted_by:
            word = separator.join(map(lambda x: x.lstrip('0'), word.split(separator)))
        return word

