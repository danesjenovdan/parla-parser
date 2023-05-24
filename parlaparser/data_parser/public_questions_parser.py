from .base_parser import BaseParser

from datetime import datetime
from .utils import fix_name
import logging
logger = logging.getLogger('session logger')


class PublicQuestionParser(BaseParser):
    base_url = 'http://parlament.ba'

    def __init__(self, data, reference):

        logger.debug('\n \n \n \n')
        logger.debug( '============= PublicQuestionParser ====================')
        logger.debug('Data: %s', data)
        logger.debug('==========================================================')

        # call init of parent object
        super(PublicQuestionParser, self).__init__(reference)

        self.storage = reference.storage
        self.public_question_storage = reference.storage.public_question_storage

        # copy item to object
        self.text = data['text']
        self.date = data['date']
        self.gov_id = data['gov_id']
        self.type = data['type']
        if data['type'] == 'question':
            if self.public_question_storage.check_if_public_question_is_parsed({'gov_id': self.gov_id}):
                logger.debug("This question is already parsed")
            else:
                # save new question
                self.person_name = data['person_name']
                date = datetime.strptime(self.date, "%d.%m.%Y").isoformat()
                person = self.storage.people_storage.get_or_add_person(
                    self.person_name.strip()
                )

                # prepere dictionary for setters
                public_question = {
                    'created_at': date,
                    'approved_at': date,
                    'gov_id': self.gov_id,
                    'text': self.text,
                    'recipient_person': person.id,
                    'mandate': self.storage.mandate_id
                }
                self.public_question_storage.set_public_question(public_question)
        elif data['type'] == 'answer':
            if self.public_question_storage.check_if_public_answer_is_parsed({'gov_id': self.gov_id}):
                logger.debug("This answer is already parsed")
            else:
                question_gov_id = data['question_gov_id']
                public_question = self.public_question_storage.get_public_question(question_gov_id)
                date = datetime.strptime(self.date, "%d.%m.%Y").isoformat()
                public_answer = {
                    'created_at': date,
                    'approved_at': date,
                    'gov_id': self.gov_id,
                    'text': self.text,
                    'question': public_question.id,
                    'mandate': self.storage.mandate_id
                }
                self.public_question_storage.set_public_answer(public_answer)
