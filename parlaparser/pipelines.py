# -*- coding: utf-8 -*-
from parlaparser.settings import API_AUTH, MANDATE, MANDATE_STARTIME, MAIN_ORG_ID, API_URL

from parlaparser.spiders.questions_spider import QuestionsSpider
from parlaparser.spiders.act_spider import ActSpider
from parlaparser.spiders.session_spider import SessionSpider
from parlaparser.spiders.javna_rasprava_spider import PublicQuestionsSpider

from datetime import datetime

from parlaparser.data_parser.question_parser import QuestionParser
from parlaparser.data_parser.act_parser import ActParser
from parlaparser.data_parser.session_parser import SessionParser
from parlaparser.data_parser.public_questions_parser import PublicQuestionParser

from parladata_base_api.storages.storage import DataStorage
from parladata_base_api.storages.agenda_item_storage import AgendaItem

import logging
logger = logging.getLogger('pipeline logger')



class BihParserPipeline(object):
    mandate_start_time = datetime(day=1, month=12, year=2018)
    def __init__(self):
        print('Init')

        self.storage = DataStorage(
            MANDATE, MANDATE_STARTIME, MAIN_ORG_ID, API_URL, API_AUTH[0], API_AUTH[1]
        )
        self.storage.default_procedure_phase = 1
        AgendaItem.keys = ["name", "session"]

    # def open_spider(self, spider):
    #     print('Open spider')
    #     if spider.name == 'acts':
    #         self.storage.session_storage.load_data()
    #         self.storage.legislation_storage.load_data()

    #     elif spider.name == 'questions':
    #         self.storage.session_storage.load_data()
    #         self.storage.question_storage.load_data()

    #     elif spider.name == 'sessions':
    #         self.storage.session_storage.load_data()
    #         self.storage.legislation_storage.load_data()
    #     elif spider.name == 'javnarasprava':
    #         self.storage.public_question_storage.load_data()


    def process_item(self, item, spider):
        if type(spider) == QuestionsSpider:
            QuestionParser(item, self)
        elif type(spider) == ActSpider:
            ActParser(item, self)
        elif type(spider) == SessionSpider:
            SessionParser(item, self)
        elif type(spider) == PublicQuestionsSpider:
            PublicQuestionParser(item, self)
        else:
            return item

