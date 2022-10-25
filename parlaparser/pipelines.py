# -*- coding: utf-8 -*-

from .settings import API_AUTH

from parlaparser.spiders.speech_spider import SpeechSpider
from parlaparser.spiders.votes_spider import VotesSpider
from parlaparser.spiders.comitee_spider import ComiteeSpider
from parlaparser.spiders.questions_spider import QuestionsSpider

from datetime import datetime

from .data_parser.question_parser import QuestionParser
from .data_parser.person_parser import PersonParser
from .data_parser.act_parser import ActParser
from .data_parser.club_parser import ClubParser
from .data_parser.session_parser import SessionParser
#-----------------------------------------------
from parlaparser.data_parser.speech_parser import SpeechParser
from parlaparser.data_parser.vote_parser import BallotsParser
from parlaparser.data_parser.base_parser import HRDataStorage
from parlaparser.data_parser.comitee_parser import ComiteeParser

from parladata_storage.storage import DataStorage

import logging
logger = logging.getLogger('pipeline logger')



class ParlaparserPipeline(object):
    mandate_start_time = datetime(day=1, month=12, year=2018)
    def __init__(self):
        self.storage = HRDataStorage()

    def process_item(self, item, spider):
        if type(spider) == SpeechSpider:
            SpeechParser(item, self)
        elif type(spider) == VotesSpider:
            BallotsParser(item, self)
        elif type(spider) == QuestionsSpider:
            QuestionParser(item, self)
        elif type(spider) == ComiteeSpider:
            ComiteeParser(item, self)
        else:
            return item

