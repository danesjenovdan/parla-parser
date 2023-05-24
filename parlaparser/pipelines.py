# -*- coding: utf-8 -*-
from .settings import API_AUTH

from parlaparser.spiders.people_spider import PeopleSpider
from parlaparser.spiders.questions_spider import QuestionsSpider
from parlaparser.spiders.act_spider import ActSpider
from parlaparser.spiders.club_spider import ClubSpider
from parlaparser.spiders.session_spider import SessionSpider
from parlaparser.spiders.javna_rasprava_spider import PublicQuestionsSpider

from datetime import datetime

from requests.auth import HTTPBasicAuth
import requests

from .data_parser.question_parser import QuestionParser
from .data_parser.person_parser import PersonParser
from .data_parser.act_parser import ActParser
from .data_parser.club_parser import ClubParser
from .data_parser.session_parser import SessionParser
from .data_parser.public_questions_parser import PublicQuestionParser

from parse_utils.storage.storage import DataStorage

import logging
logger = logging.getLogger('pipeline logger')



class BihParserPipeline(object):
    mandate_start_time = datetime(day=1, month=12, year=2018)
    def __init__(self):
        self.storage = DataStorage()
        print('Init')

    def open_spider(self, spider):
        print('Open spider')
        if spider.name == 'acts':
            self.storage.session_storage.load_data()
            self.storage.legislation_storage.load_data()

        elif spider.name == 'questions':
            self.storage.session_storage.load_data()
            self.storage.question_storage.load_data()

        elif spider.name == 'sessions':
            self.storage.session_storage.load_data()
            self.storage.legislation_storage.load_data()
        elif spider.name == 'javnarasprava':
            self.storage.public_question_storage.load_data()


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
        elif type(spider) == PublicQuestionsSpider:
            PublicQuestionParser(item, self)
        else:
            return item

