from .utils import fix_name, name_parser

from ..settings import API_URL, API_AUTH

from requests.auth import HTTPBasicAuth

import requests
import editdistance

from datetime import datetime

import logging
logger = logging.getLogger('base logger')

class BaseParser(object):
    def __init__(self, reference):
        self.reference = reference

    # TODO
    def api_request(self, endpoint, dict_key, value_key, json_data, method='post'):
        if value_key in getattr(self.reference, dict_key).keys() and not method =='patch':
            obj_id = getattr(self.reference, dict_key)[value_key]
            return obj_id, 'get'
        else:
            requests_method = getattr(requests, method)
            response = requests_method(
                API_URL + endpoint,
                json=json_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            logger.debug(response.status_code)
            try:
                obj_id = response.json()['id']
                getattr(self.reference, dict_key)[value_key] = obj_id
            except Exception as e:
                logger.debug(response.content)
                logger.debug(endpoint, e, response.text, 'request was not delivered request was not delivered request was not delivered request was not delivered')
                return None, 'fail'
        return obj_id, 'set'


    def get_agenda_item(self, value_key, json_data):
        return self.api_request('agenda-items/', 'agenda_items', value_key, json_data)


    def get_or_add_person(self, name, districts=None, mandates=None, education=None, birth_date=None, gov_id=None):
        person_id = self.get_person_id(name)
        if not person_id:
            person_data = {
                'name': fix_name(name),
                'name_parser': name_parser(name),
                'gov_id': gov_id
            }
            if districts:
                person_data['districts'] = districts
            if mandates:
                person_data['mandates'] = mandates
            if education:
                person_data['education'] = education
            if birth_date:
                person_data['birth_date'] = birth_date
            logger.debug('Adding person', person_data)
            response = requests.post(
                API_URL + 'persons/',
                json=person_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
            logger.debug("NEWWW PERSON  check it: ", name)
            try:
                person_id = response.json()['id']
                self.reference.members[name] = person_id
            except Exception as e:
                logger.debug(e, response.json())
                return None
        return person_id

    def get_person_id(self, name):
        for key in self.reference.members.keys():
            for parser_name in key.split(','):
                if editdistance.eval(name.lower(), parser_name) < 2:
                    return self.reference.members[key]
        return None

    def add_or_get_motion(self, value_key, json_data):
        return self.api_request('motions/', 'motions', value_key, json_data)

    def add_or_get_area(self, value_key, json_data):
        return self.api_request('areas/', 'areas', value_key, json_data)

    def add_or_get_vote(self, value_key, json_data):
        return  self.api_request('votes/', 'votes', value_key, json_data)

    def update_vote(self, value_key, json_data, id=None):
        return  self.api_request('votes/' + str(id) + '/' if id else '', 'votes', value_key, json_data, method='patch')

    def update_legislation(self, value_key, json_data, id=None):
        response = requests.patch(
                API_URL + 'law/' + str(id) + '/',
                json=json_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
        data = response.json()
        self.reference.legislation[value_key] = data
        return data

    def add_legislation(self, value_key, json_data):
        response = requests.post(
                API_URL + 'law/',
                json=json_data,
                auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
            )
        data = response.json()
        self.reference.legislation[value_key] = data
        return data

    def add_or_get_question(self, value_key, json_data):
        return  self.api_request('questions/', 'questions', value_key, json_data)

    def add_link(self, json_data):
        return  self.api_request('links/', 'links', json_data['url'], json_data)

    def add_ballot(self, voter, vote, option, party=None):
        json_data ={
            'option': option,
            'vote': vote,
            'voter': voter,
            'voterparty': self.reference.others
        }
        if party:
            json_data.update({"voterparty": party})
        response = requests.post(
            API_URL + 'ballots/',
            json=json_data,
            auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        )
        logger.debug(response.text)

    def add_ballots(self, json_data):
        logger.debug("SENDING BALLOTS")
        response = requests.post(
            API_URL + 'ballots/',
            json=json_data,
            auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
        )
        #logger.debug(response.content)

    def add_or_get_session(self, session_name, json_data):
        if session_name:
            return  self.api_request('sessions/', 'sessions', session_name, json_data)
        else:
            return None

    def parse_edoc_person(self, data):
        splited = data.split('(')
        logger.debug(splited)
        name = splited[0]
        if len(splited) > 1:
            pg = splited[1].split(')')[0]
            logger.debug(pg)
        else:
            # ministers names are splited with /
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
        return name, pg

    def get_organization_id(self, name, classification='pg'):
        p = False
        #if 'mora' in name:
        #    p = True
        if classification=='commitee':
            org_class = 'commitee'
        else:
            org_class = 'parties'

        for key in getattr(self.reference, org_class).keys():
            for parser_name in key.split('|'):
                #if p:
                #    logger.debug(parser_name, editdistance.eval(name, parser_name))
                if editdistance.eval(name, parser_name) < 1:
                    return getattr(self.reference, org_class)[key]
        return None

    def add_organization(self, name, classification, create_if_not_exist=True):
        party_id = self.get_organization_id(name, classification)

        if not party_id:
            if create_if_not_exist:
                logger.debug("ADDING ORG " + name)
                response = requests.post(API_URL + 'organizations/',
                                         json={"_name": name.strip(),
                                               "name": name.strip(),
                                               "name_parser": name.strip(),
                                               "_acronym": name[:100],
                                               "classification": classification},
                                         auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                        )

                try:
                    party_id = response.json()['id']
                    self.reference.parties[name.strip()] = party_id
                except Exception as e:
                    logger.debug(e, response.json())
                    return None
            else:
                return None

        return party_id

    def add_membership(self, person_id, party_id, role, label, start_time, on_behalf_of=None):
        response = requests.post(API_URL + 'memberships/',
                                 json={"person": person_id,
                                       "organization": party_id,
                                       "role": role,
                                       "label": label,
                                       "start_time": start_time,
                                       "on_behalf_of": on_behalf_of},
                                 auth=HTTPBasicAuth(API_AUTH[0], API_AUTH[1])
                                )
        membership_id = response.json()['id']
        return membership_id

    def get_membership_of_member_on_date(self, person_id, search_date):
        memberships = self.reference.memberships
        if person_id in memberships.keys():
            # person in member of parliamnet
            mems = memberships[str(person_id)]
            for mem in mems:
                start_time = datetime.strptime(mem['start_time'], "%Y-%m-%dT%H:%M:%S")
                if start_time <= search_date:
                    if mem['end_time']:
                        end_time = datetime.strptime(mem['end_time'], "%Y-%m-%dT%H:%M:%S")
                        if end_time >= search_date:
                            return mem['on_behalf_of']
                    else:
                        return mem['on_behalf_of']
        return None

    def remove_leading_zeros(self, word, separeted_by=[',', '-', '/']):
        for separator in separeted_by:
            word = separator.join(map(lambda x: x.lstrip('0'), word.split(separator)))
        return word

