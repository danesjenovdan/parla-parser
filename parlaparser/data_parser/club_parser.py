from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from .utils import parse_date, fix_name
from datetime import datetime

class ClubParser(BaseParser):
    def __init__(self, item, reference):
        # call init of parent object
        super(ClubParser, self).__init__(reference)
        self.club_name = item['club_name'] 
        self.role = item['role']
        self.member = item['member']

        self.start_time = self.reference.mandate_start_time.isoformat()

        # prepere dictionarys for setters

        self.get_person_data(item)

    def get_person_data(self, item):

        person_id = self.get_or_add_person(
            fix_name(self.member)
        )

        party_id = self.add_organization(self.club_name, "pg")

        # spremni to da lahko urejaš on behalf_of in organization
        self.add_membership(person_id, self.reference.commons_id, 'voter', 'cl', self.start_time, on_behalf_of=party_id)
        self.add_membership(person_id, party_id, self.role, 'cl', self.start_time, on_behalf_of=None)
