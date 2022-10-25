from .base_parser import BaseParser
from parladata_storage.agenda_item_storage import AgendaItem

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests

class SpeechParser(BaseParser):
    def __init__(self, data, reference):
        """{"date": "20.04.2018.",
        "session_ref": ["Saziv: IX, sjednica: 8"],
        "content_list": ["Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254", "Prijedlog zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na Republiku Hrvatsku, prvo \u010ditanje, P.Z. br. 254"],
        "speaker": ["Brki\u0107, Milijan (HDZ)"],
        "order": 1,
        "content": "Prelazimo na sljede\u0107u to\u010dku dnevnog reda, Prijedlog Zakona o izmjenama i dopuni Zakona o prijenosu osniva\u010dkih prava nad Sveu\u010dili\u0161tem Sjever na RH, prvo \u010ditanje, P.Z. br. 254.\nPredlagatelj je zastupnik kolega Robert Podolnjak na temelju \u010dlanka 85. Ustava RH i \u010dlanka 172. Poslovnika Hrvatskog sabora.\nPrigodom rasprave o ovoj to\u010dki dnevnog reda primjenjuju se odredbe Poslovnika koji se odnose na prvo \u010ditanje zakona.\nRaspravu su proveli nadle\u017eni Odbor za zakonodavstvo, nadle\u017eni Odbor za obrazovanje, znanost i kulturu.\nVlada je dostavila svoje mi\u0161ljenje.\nPozivam po\u0161tovanog kolegu gospodina Roberta Podolnjaka da nam da dodatno obrazlo\u017eenje prijedloga Zakona.\nIzvolite."},
        """
        # call init of parent object
        speeches = data['speeches']
        super(SpeechParser, self).__init__(reference)

        self.storage = reference.storage

        self.speeches = []

        organization = self.storage.organization_storage.get_or_add_organization(
            'Sabor',
        )
        gov_id = data['agenda_id']
        session = data['session_ref'][0].split(':')[-1].strip()
        self.date = datetime.strptime(data['date'], API_DATE_FORMAT + '.')

        session_data = {
            "organization": organization.id,
            "mandate": self.storage.mandate_id,
            "organizations": [organization.id],
            "in_review": False,
            "gov_id": gov_id,
            "name": session + ". sjednica",
            "classification": 'regular',
            'start_time': self.date.isoformat()
        }

        # get and set session
        session = self.storage.session_storage.add_or_get_session(session_data)
        session.load_agenda_items()

        self.agenda_ids = []
        methods = []
        for ai in data['agendas']:
            agenda_text = ai['text']
            ai_order = ai['order'] if ai['order'].isdigit() else None
            agenda_json = {
                "name": agenda_text.strip(),
                "datetime": self.date.isoformat(),
                "session": session.id,
                "order": gov_id,
                "gov_id": gov_id
            }
            # agenda_key = AgendaItem.get_key_from_dict(agenda_json)

            agenda_item = session.agenda_items_storage.get_or_add_agenda_item(agenda_json)
            self.agenda_ids.append(agenda_item.id)
            #print(agenda_method, agenda_text.strip())
            methods.append(agenda_item.is_new)

        # skip adding speeches if any agenda_item already exists
        if not any(methods):
            #print("SETTING", self.session_id)
            for speech in speeches:

                self.speaker = speech['speaker']
                self.order = speech['order']
                self.content = speech['content']
                # SPEECH

                self.speech = {'session': session.id}

                self.parse_time()
                self.set_data()
            session.add_speeches(self.speeches)
            #if response.status_code == 400:
            #    print(response.status_code)
        elif agenda_item.is_new == None:
            print('agenda item set failed')
        else:
            #print('this agenda item allready parsed')
            pass

    def parse_time(self):
        self.speech['valid_from'] = self.date.isoformat()
        self.speech['start_time'] = self.date.isoformat()
        self.speech['valid_to'] = datetime.max.isoformat()

    def set_data(self):
        self.speech['content'] = self.content
        self.speech['order'] = self.order

        self.speech['agenda_items'] = self.agenda_ids

        # get and set speaket
        speaker, pg = self.parse_edoc_person(self.speaker[0])
        speaker = self.storage.people_storage.get_or_add_person(speaker)

        self.speech['speaker'] = speaker.id

        self.speeches.append(self.speech)
