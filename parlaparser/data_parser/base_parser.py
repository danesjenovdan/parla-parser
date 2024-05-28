from .utils import fix_name, name_parser

from ..settings import API_URL, API_AUTH

from parladata_storage import storage
from parladata_storage import session_storage

from requests.auth import HTTPBasicAuth

import requests
import editdistance

from datetime import datetime

import logging
logger = logging.getLogger('base logger')

class HRSession(session_storage.Session):
    def get_key(self) -> str:
        return f'{self.name.strip().lower()}_{self.organizations[0]}'

    @classmethod
    def get_key_from_dict(ctl, data) -> str:
        return (data['name'].strip().lower() + '_' + str(data['organizations'][0])).strip().lower()

class HRSessionStorage(session_storage.SessionStorage):
    sessionClass = HRSession

class HRDataStorage(storage.DataStorage):
    def __init__(self):
        logging.warning(f'Start loading data')
        self.parladata_api = storage.ParladataApi()

        self.session_storage = HRSessionStorage(self)
        self.legislation_storage = storage.LegislationStorage(self)
        self.legislation_storage.load_data()
        self.people_storage = storage.PeopleStorage(self)
        self.organization_storage = storage.OrganizationStorage(self)
        self.question_storage = storage.QuestionStorage(self)
        self.membership_storage = storage.MembershipStorage(self)
        self.membership_storage.load_data()

class BaseParser(object):
    def __init__(self, reference):
        self.reference = reference

    def parse_edoc_person(self, data):
        splited = data.split('(')
        name = splited[0]
        if len(splited) > 1:
            pg = splited[1].split(')')[0]
        else:
            splited = data.split('/')
            if len(splited) > 1:
                name = splited[0]
                pg = splited[1].strip()
                if ';' in pg:
                    pg = pg.replace(';', '')
                if 'Vlade' in pg:
                    pg = 'gov'
            else:
                pg = None
        name = ' '.join(reversed(list(map(str.strip, name.split(',')))))
        return (name, pg)

    def remove_leading_zeros(self, word, separeted_by=[',', '-', '/']):
        for separator in separeted_by:
            word = separator.join(map(lambda x: x.lstrip('0'), word.split(separator)))
        return word
