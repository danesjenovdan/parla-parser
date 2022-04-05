# -*- coding: utf-8 -*-
from .settings import API_AUTH

from bihparser.spiders.people_spider import PeopleSpider
from bihparser.spiders.questions_spider import QuestionsSpider
from bihparser.spiders.act_spider import ActSpider
from bihparser.spiders.club_spider import ClubSpider
from bihparser.spiders.session_spider import SessionSpider

from datetime import datetime

from requests.auth import HTTPBasicAuth
import requests

from .data_parser.question_parser import QuestionParser
from .data_parser.person_parser import PersonParser
from .data_parser.act_parser import ActParser
from .data_parser.club_parser import ClubParser
from .data_parser.session_parser import SessionParser

from bihparser.storage.storage import DataStorage

import logging
logger = logging.getLogger('pipeline logger')



class BihParserPipeline(object):
    mandate_start_time = datetime(day=1, month=12, year=2018)
    def __init__(self):
        self.storage = DataStorage()


    def process_item(self, item, spider):
        if type(spider) == PeopleSpider:
            PersonParser(item, self)
        elif type(spider) == ClubSpider:
            logger.warning("club_spider")
            ClubParser(item, self)
        elif type(spider) == QuestionsSpider:
            QuestionParser(item, self)
        elif type(spider) == ActSpider:
            ActParser(item, self)
        elif type(spider) == SessionSpider:
            SessionParser(item, self)
        else:
            return item

