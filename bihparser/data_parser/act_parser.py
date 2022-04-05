from .base_parser import BaseParser
from .utils import get_vote_key

from ..settings import API_URL, API_AUTH, API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests


options_map = {
    """ CROATIANS
    'donesen': 'enacted',
    'dostavljeno radi informiranja': 'submitted',
    'odbijen': 'rejected',
    'povučen': 'retracted',
    'prihvaćen': 'adopted',
    'prima se na znanje': 'received',
    'u proceduri': 'in_procedure',
    """

    'Čeka na pokretanje procedure': 'received',
    'Donesen': 'enacted',
    'Donesen - čeka se odluka Ustavnog suda BiH': 'enacted',
    'Donesen - odlukom Ustavnog suda BiH - stavljen van snage': 'enacted',
    'Donesen - u cjelosti ukinut Odlukom Ustavnog suda BiH o dopustivosti i meritumu': 'enacted',
    'Nije razmatran': 'fake',
    'Obustavljen postupak': 'fake',
    'Odbijen': 'rejected',
    'Odbijen - povučen': 'rejected',
    'Ostaje na snazi': 'fake',
    'Povučen': 'retracted',
    'Procedura': 'in_procedure',
    'Procedura - nije preuzet': 'in_procedure',
    'Proglašen na privremenim osnovama - ostaje na snazi': 'in_procedure',
    'Ukinut Odlukom Ustavnog suda BiH':  'fake',
    'Umiren postupak': 'fake',
}


class ActParser(BaseParser):
    def __init__(self, data, reference):
        """
        {
            #"ref_ses": ["IX-2"],
            #"signature": ["IX-73/2016"],
            #"ballots": ["81/8/22"],
            #"pub_title": ["Odluka o davanju suglasnosti na Polugodi\u0161nji izvje\u0161taj o izvr\u0161enju Financijskog plana Dr\u017eavne agencije za osiguranje \u0161tednih uloga i sanaciju banaka za prvo polugodi\u0161te 2016. godine"],
            #"mdt": ["Vlada RH"],
            #"title": ["Polugodi\u0161nji izvje\u0161taj o izvr\u0161enju Financijskog plana Dr\u017eavne agencije za osiguranje \u0161tednih uloga i sanaciju banaka u prvom polugodi\u0161tu 2016. godine"],
            "voting": ["ve\u0107inom glasova"],
            #"pdf": ["../NewReports/GetReport.aspx?reportType=1&id=2020972&loggedInUser=False"],
            #"agenda_no": ["4."],
            #"date_vote": ["\r\n                        \r\n                        ", "25.11.2016.", "\r\n                        ", "\r\n                        ", "\r\n\t\t\t\t\t\r\n                            \r\n                            ", "\r\n                        \r\n\t\t\t\t", "\r\n                    "],
            #"result": ["81/8/22"],
            #"status": ["donesen i objavljen"],
            "dates": ["24.11.2016.; 25.11.2016."]},

            {
            # 'date': '66.,   3.9.2018. ',
            # 'epa': ' 01,02-02-1-753/18, od 15.3.2018. ',
            'faza': ' Procedura - UPK je utvrdila da je PZ usaglašen sa Ustavom BiH i pravnim sistemom BiH ',
            # 'mdt': ' Zajednička komisija za odbranu i sigurnost BiH ',
            # 'session': ' 120 sjednica, održana 9.11.2017. ',
            # 'status': 'Procedura',
            # 'title': 'Prijedlog zakona o izmjenama i dopunama Zakona o deminiranju u Bosni i Hercegovini',
            #'uid': '123123'
            }
        """
        # call init of parent object        
        super(ActParser, self).__init__(reference)

        self.act = data

        #self.title = data['text'] # REMOVE
        #self.mdt = data['mdt'] # REMOVE
        self.uid = data['uid']

        if 'date' in data.keys() and data['date']:
            date = data['date'].split(',')[1].strip()
            self.date = datetime.strptime(date, API_DATE_FORMAT + '.')
        else:
            date = data['epa'].split('od')[1].strip()
            self.date = datetime.strptime(date, API_DATE_FORMAT + '.')

        self.status = data['status']
        self.epa = data['epa'].split(', ')[0].strip()
        
        #try:
        #    self.voting = data['voting'][0]
        #except:
        #    self.voting = ''

        # dont parse session of Legislation TODO: when comes sessions with legislation fix this
        #if 'session' in self.act.keys():
        #    self.session_name = data['session'].split(',')[0].strip()
        #    self.session = {
        #        "organization": self.reference.commons_id,
        #        "organizations": [self.reference.commons_id],
        #        "in_review": False,
        #        "name": self.session_name,
        #        "start_time": self.date.isoformat() 
        #    }
        #else:
        self.session = None

        act_api_status = self.act_status()
        if act_api_status == 'unknown':
            self.parse_data()
            #logger.debug(self.act)
            self.add_act(self.uid, self.act)
        elif act_api_status == 'in process':
            # TODO compare and edit
            self.parse_data()
        else:
            #logger.debug('law is finished')
            self.parse_data()
            pass

    def parse_data(self):
        if self.session:
            session_id, session_status = self.add_or_get_session(self.session_name, self.session)
            self.act['session'] = session_id
        else:
            self.act['session'] = None
        #this already in act data
        #self.act['text'] = self.title
        #self.act['mdt'] = self.mdt
        #self.act['uid'] = self.uid
        self.act['epa'] = self.epa
        self.act['classification'] = 'legislation' if self.epa else 'akt' 

        #if 'Vlada HR' in self.mdt:
        #    self.mdt = self.mdt.replace('HR')
        if 'mdt' in self.act.keys():
            mdt_fk = self.add_organization(self.act['mdt'].strip(), 'commitee', create_if_not_exist=True)
            self.act['mdt_fk'] = mdt_fk
        self.act['procedure_phase'] = self.status

        try:
            self.act['status'] = options_map[self.status]
        except:
            self.act['status'] = 'under_consideration'

        self.act['procedure_phase'] = self.status
        """
        options = {
            'odbijen': 'rejected',
            'prihvaćen': None,
            'donesen': 'accepted',
            'prima se na znanje': 'accepted',
            }
        """
        try:
            self.act['result'] = options_map[self.status]
        except:
            self.act['result'] = 'in_procedure'

        if self.act['result'] in ['accepted', 'rejected']:
            self.act['procedure_ended'] = True

        self.act['date'] = self.date.isoformat()
        #self.act['procedure'] = self.voting

    def act_status(self):
        if self.uid.strip() in self.reference.acts.keys():
            act = self.reference.acts[self.uid]
            if act['ended']:
                return 'ended'
            else:
                return 'in process'
        else:
            return 'unknown'


    def add_act(self, uid, json_data):
        act_id, method = self.api_request('law/', 'acts', uid, json_data)
        if 'procedure_ended' in json_data.keys():
            ended = True
        else:
            ended = False
        self.reference.acts[uid] = {"id": act_id, "ended": ended}





