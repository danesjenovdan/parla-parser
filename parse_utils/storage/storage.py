from parlaparser import settings
from parse_utils.parladata_api import ParladataApi
from parse_utils.storage.session_storage import SessionStorage
from parse_utils.storage.legislation_storage import LegislationStorage
from parse_utils.storage.question_storage import QuestionStorage
from parse_utils.storage.public_question_storage import PublicQuestionStorage
from parse_utils.storage.people_storage import PeopleStorage
from parse_utils.storage.organization_storage import OrganizationStorage
from parse_utils.storage.agenda_item_storage import AgendaItemStorage
from parse_utils.storage.membership_storage import MembershipStorage

from collections import defaultdict
from datetime import datetime

import logging
import editdistance


class NoneError(Exception):
    pass


class DataStorage(object):

    memberships = defaultdict(lambda: defaultdict(list))

    mandate_start_time = settings.MANDATE_STARTIME
    mandate_id = settings.MANDATE
    main_org_id = settings.MAIN_ORG_ID
    # old end

    def __init__(self):
        logging.warning(f'Start loading data')
        self.parladata_api = ParladataApi()

        self.session_storage = SessionStorage(
            self,
            motion_keys=('text', 'datetime')
        )
        self.legislation_storage = LegislationStorage(self)
        self.people_storage = PeopleStorage(self)
        self.organization_storage = OrganizationStorage(self)
        self.question_storage = QuestionStorage(self)
        self.public_question_storage = PublicQuestionStorage(self)
        self.agenda_item_storage = AgendaItemStorage(self)
        self.membership_storage = MembershipStorage(self)



    # area
    def set_area(self, data):
        added_area = self.parladata_api.set_area(data)
        return added_area.json()


    # links
    def set_link(self, data):
        added_link = self.parladata_api.set_link(data)
        return added_link

    def set_org_membership(self, data):
        added_link = self.parladata_api.set_org_membership(data)
        return added_link

    def set_mandate(self, data):
        added_mandate = self.parladata_api.set_mandate(data)
        return added_mandate

