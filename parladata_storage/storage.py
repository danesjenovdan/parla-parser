from parlaparser import settings
from parladata_storage.parladata_api import ParladataApi
from parladata_storage.session_storage import SessionStorage
from parladata_storage.legislation_storage import LegislationStorage
from parladata_storage.question_storage import QuestionStorage
from parladata_storage.people_storage import PeopleStorage
from parladata_storage.organization_storage import OrganizationStorage
from parladata_storage.membership_storage import MembershipStorage

from collections import defaultdict
from datetime import datetime

import logging


class NoneError(Exception):
    pass


class DataStorage(object):

    memberships = defaultdict(lambda: defaultdict(list))

    mandate_start_time = settings.MANDATE_STARTIME
    mandate_id = settings.MANDATE
    main_org_id = settings.MAIN_ORG_ID
    default_procedure_phase = 1
    # old end

    def __init__(self):
        logging.warning(f'Start loading data')
        self.parladata_api = ParladataApi()

        self.session_storage = SessionStorage(self)
        self.legislation_storage = LegislationStorage(self)
        self.people_storage = PeopleStorage(self)
        self.organization_storage = OrganizationStorage(self)
        self.question_storage = QuestionStorage(self)
        self.membership_storage = MembershipStorage(self)

    # area
    def set_area(self, data):
        added_area = self.parladata_api.set_area(data)
        return added_area.json()


    # links
    def set_link(self, data):
        added_link = self.parladata_api.set_link(data)
        return added_link
