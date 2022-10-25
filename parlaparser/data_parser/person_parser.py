from .base_parser import BaseParser

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT
from .utils import parse_date, fix_name
from datetime import datetime

class PersonParser(BaseParser):
    def __init__(self, item, reference):
        # call init of parent object
        super(PersonParser, self).__init__(reference)
        self.name = item['name']
        self.area = item['area']
        #self.education = item['education']
        self.party = item['party']
        self.klub = item['klub']
        self.wbs = item['wbs']
        self.person_type = item['type']
        print(self.name)
        try:
            self.start_time = parse_date(item['start_time']).isoformat()
        except:
            self.start_time = self.reference.mandate_start_time.isoformat()

        # prepere dictionarys for setters
        self.person = {}
        self.area_data = {
            "name": item['area'],
            "calssification": "district"
        }

        if self.get_person_id(self.name):
            print("Alredy exists")
            pass
        else:
            self.get_person_data(item)

    def get_person_data(self, item):
        gov_id = item['url'].split('/')[-1]
        area_id, method = self.add_or_get_area(item['area'], self.area_data)
        if area_id:
            area = [area_id]
        else:
            area = []

        person_id = self.get_or_add_person(
            fix_name(self.name),
            districts=area,
            gov_id=gov_id,
            #mandates=self.num_of_prev_mandates,
            #education=edu,
            #birth_date=self.birth_date
        )
        print(self.person_type)

        if self.person_type.startswith("Poslanici"):
            party_id = self.add_organization(self.party, "party")
            core_org = self.reference.commons_id
        else:
            party_id = self.add_organization(self.klub, "club")
            core_org = self.reference.people_id
        print(party_id)
        self.add_membership(
            person_id,
            party_id,
            'member',
            'cl',
            self.start_time
        )
        self.add_membership(
            person_id,
            core_org,
            'voter',
            'cl',
            self.start_time,
            on_behalf_of=party_id
        )

        if 'wbs' in item.keys():
            for typ, names in self.wbs.items():
                for name in names:
                    wb_id = self.add_organization(name, typ)
                    self.add_membership(
                        person_id,
                        wb_id,
                        'member',
                        'member',
                        self.reference.mandate_start_time.isoformat()
                    )
