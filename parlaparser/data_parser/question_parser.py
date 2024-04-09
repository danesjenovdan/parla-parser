from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from .utils import fix_name
from pprint import pprint
import re
import logging
logger = logging.getLogger('session logger')


class QuestionParser(BaseParser):
    base_url = 'http://parlament.ba'

    def __init__(self, data, reference):

        logger.debug('\n \n \n \n')
        logger.debug( '============= QuestionParser ====================')
        logger.debug('Data: %s', data)
        logger.debug('==========================================================')

        # call init of parent object
        super(QuestionParser, self).__init__(reference)

        self.storage = reference.storage
        self.question_storage = reference.storage.question_storage

        # copy item to object
        self.author = data['name']
        self.title = data['text']
        self.signature = data['ref']
        self.date = data['date']
        self.recipient = data['asigned']
        self.links = data['links']
        self.session = data.get('session', None)

        # prepere dictionarys for setters
        self.question = {
            'type_of_question': 'question',
            'mandate': self.storage.mandate_id,
        }
        self.date_f = None

        if self.question_storage.check_if_question_is_parsed({'gov_id': self.signature}):
            # TODO edit question if we need it make force_render mode
            logger.debug("This question is already parsed")

        else:
            # parse data
            self.parse_time()
            self.parse_data()


    def get_question_id(self):
        return self.reference.questions[self.signature]

    def parse_time(self):
        sp = self.date.split(',')
        date = sp[-1].strip()
        self.date_f = datetime.strptime(date, "%d.%m.%Y.")
        self.question['timestamp'] = self.date_f.isoformat()

    def parse_data(self):
        self.question['gov_id'] = self.signature
        self.question['title'] = self.title

        if not self.author.strip():
            logger.debug('************** self.author is empty')
        else:
            author_ids = []
            author_org_ids = []
            author = self.storage.people_storage.get_or_add_person(
                fix_name(self.author),
            )

            author_ids.append(author.id)

            if self.session:
                session_name = self.session.split(',')
                session = self.storage.session_storage.get_session_by_name(session_name[0].strip())
                if session:
                    self.question['session'] = session.id

            self.question['person_authors'] = author_ids
            self.question['organization_authors'] = author_org_ids
            self.question['recipient_text'] = self.recipient.strip() if self.recipient else None

            logger.debug('*'*60)
            logger.debug('Question: %s', self.question)
            logger.debug('*'*60)

            # send question
            question = self.question_storage.add_or_get_question(self.question)

            # send link
            if question.is_new and self.links:
                for link in self.links:
                    if link['url']:
                        link['question'] = question.id
                        link['url'] = self.base_url + link['url']
                        self.storage.set_link(link)
