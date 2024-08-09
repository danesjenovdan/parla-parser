# -*- coding: utf-8 -*-

from parlaparser.settings import *

from parlaparser.spiders.speech_spider import SpeechSpider
from parlaparser.spiders.votes_spider import VotesSpider
from parlaparser.spiders.comitee_spider import ComiteeSpider
from parlaparser.spiders.questions_spider import QuestionsSpider
from parlaparser.spiders.membership_spider import MembershipSpider

from datetime import datetime

from parlaparser.data_parser.question_parser import QuestionParser
from parlaparser.data_parser.speech_parser import SpeechParser
from parlaparser.data_parser.vote_parser import BallotsParser
from parlaparser.data_parser.comitee_parser import ComiteeParser
from parlaparser.data_parser.membership_parser import MembershipParser, ImageParser

from parladata_base_api.storages.storage import DataStorage
from parladata_base_api.storages.session_storage import Session
from parladata_base_api.storages.agenda_item_storage import AgendaItem

import logging

logger = logging.getLogger("pipeline logger")


class ParlaparserPipeline(object):
    mandate_start_time = datetime(day=1, month=12, year=2018)

    def __init__(self):
        self.storage = DataStorage(
            MANDATE, MANDATE_STARTIME, MAIN_ORG_ID, API_URL, API_AUTH[0], API_AUTH[1]
        )
        # set custom keys for ParladataBaseApi
        Session.keys = ["name", "organizations"]
        AgendaItem.keys = ["name", "session"]

    def process_item(self, item, spider):
        if type(spider) == SpeechSpider:
            SpeechParser(item, self)
        elif type(spider) == VotesSpider:
            BallotsParser(item, self)
        elif type(spider) == QuestionsSpider:
            QuestionParser(item, self)
        elif type(spider) == ComiteeSpider:
            ComiteeParser(item, self)
        elif type(spider) in [MembershipSpider, ImageParser]:
            # ImageParser(item, self)
            MembershipParser(item, self)
        else:
            return item

    def open_spider(self, spider):
        spider.myPipeline = self

    def save_memberships(self):
        MembershipParser({"type": "refresh_memberships"}, self)
