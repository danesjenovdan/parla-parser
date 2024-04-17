from .base_parser import BaseParser
from .utils import get_vote_key, fix_name, decode_ba_string

from ..settings import API_DATE_FORMAT

from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import pdftotext
import copy
import re
import time

import logging
logger = logging.getLogger('session logger')

UPDATE_VOTES = False

class SessionParser(BaseParser):
    def __init__(self, item, reference):
        """
            'gov_id': session_gov_id,
            'name': session_name,
            'start_date': start_date,
            'start_time': start_time,
            'speeches'
            'votes'
            'session_of'
        """
        # call init of parent object
        super(SessionParser, self).__init__(reference)
        logger.info('.:SESSION PARSER:.')

        self.storage = reference.storage

        self.speeches = []
        cut_order = r'^\d*\. '

        organization = self.storage.organization_storage.get_or_add_organization(
            item['session_of'],
        )

        session_data = {
            "organization": organization.id,
            "mandate": self.storage.mandate_id,
            "organizations": [organization.id],
            "in_review": False,
            "gov_id": item['gov_id'],
            "name": item['name'],
            "classification": self.get_session_type(item['name'])
        }
        self.update = UPDATE_VOTES
        # get and set session

        logger.debug('session state 1')

        start_time = datetime.strptime(item['start_date'].strip() + ' ' + item['start_time'].strip(), API_DATE_FORMAT + ' %H:%M')
        session_data['start_time'] = start_time.isoformat()

        session = self.storage.session_storage.add_or_get_session(session_data)
        session.load_votes()


        if 'agenda_items' in item.keys():
            for agenda_item in item['agenda_items']:
                agenda_text = re.sub(cut_order, '', agenda_item)
                if agenda_text[-1] == ';':
                    agenda_text = agenda_text[:-1]



        if 'speeches' in item.keys() and not session.get_speech_count():
            logger.debug('ima speeches')
            content_parser = ContentParser(item['speeches'])
            speeches = []
            for order, parsed_speech in enumerate(content_parser.speeches):

                speaker = self.storage.people_storage.get_or_add_person(
                    fix_name(parsed_speech['speaker']),
                )

                speech = {
                    'session': session.id,
                    'start_time': start_time.isoformat(),
                    'content': parsed_speech['content'],
                    'order': order,
                    'speaker': speaker.id
                }


                speeches.append(speech)
            session.add_speeches(speeches)


        if 'izvjestaj' in item.keys():
            status_order = ['','under_consideration', 'in_procedure', 'suspended', 'rejected', 'adopted', 'enacted']
            find_epa = r'[- 0-9,]*\d{3}\/\d{2}'
            legislation_parser = LegislationParser(item['izvjestaj'])
            results = legislation_parser.get_results(item['session_of'])

            for legislation in results:

                epa = self.remove_leading_zeros(legislation['epa'])

                if self.storage.legislation_storage.is_law_parsed(epa):
                    law = self.storage.legislation_storage.update_or_add_law({'epa': epa})
                    if legislation['result'] == 'enacted':
                        self.storage.legislation_storage.set_law_as_enacted(epa)
                    elif legislation['result'] == 'rejected':
                        self.storage.legislation_storage.set_law_as_rejected(epa)
                else:
                    print('save new legislation', legislation, epa)
                    split_words = [', predlagač:', ', broj:', '(prvo čitanje)']
                    text = legislation['text']
                    for split_word in split_words:
                        if split_word in text:
                            text = text.split(split_word)[0]

                    law = self.storage.legislation_storage.update_or_add_law(
                        {
                            'epa': epa,
                            'text': text,
                            'timestamp': start_time.isoformat(),
                            'session': session.id,
                            'mandate': self.storage.mandate_id,
                            'classification': self.storage.legislation_storage.legislation_classifications['law'].id,
                        },
                    )
                    if legislation['result'] == 'enacted':
                        self.storage.legislation_storage.set_law_as_enacted(epa)
                    elif legislation['result'] == 'rejected':
                        self.storage.legislation_storage.set_law_as_rejected(epa)

                self.storage.legislation_storage.prepare_and_set_legislation_consideration({
                    'epa': epa,
                    'organization': organization.id,
                    'procedure_phase': self.storage.default_procedure_phase,
                    'legislation': law.id,
                    'session': session.id,
                })


        if 'votes' in item.keys():
            logger.debug('ima votes')
            if item['session_of'] == 'Dom naroda':
                votes_parser = VotesParserPeople(item['votes'])
            elif item['session_of'] == 'Predstavnički dom':
                votes_parser = VotesParser(item['votes'])

            for order, parsed_vote in enumerate(votes_parser.votes):
                logger.debug(parsed_vote.keys())
                if 'name' in parsed_vote.keys():
                    name = parsed_vote['name'][:999]
                else:
                    name = parsed_vote['agenda_item_name'][:999]

                # vote_key = get_vote_key(org_id, parsed_vote['start_time'].isoformat())
                # if vote_key in self.reference.votes.keys():
                #     vote_id = self.reference.votes[vote_key]
                # else:
                #     vote_id = None

                if not session.vote_storage.check_if_motion_is_parsed({
                        'text': name,
                        'datetime': parsed_vote['start_time'].isoformat()
                    }):
                
                    epa = self.find_epa(parsed_vote['agenda_item_name'])
                    law = self.storage.legislation_storage.get_law(epa)
                    if law:
                        law_id = law.id
                    else:
                        law_id = None
                    logger.debug('Adding motion::::........')
                    motion_data = {
                        'session': session.id,
                        'text': name,
                        'title': name,
                        'datetime': parsed_vote['start_time'].isoformat(),
                        'epa': epa,
                        'law': law_id,
                    }
                    motion_obj = session.vote_storage.set_motion(motion_data)
                    vote_data = {
                        'name': name,
                        'timestamp': parsed_vote['start_time'].isoformat(),
                        'session': session.id,
                        'motion': motion_obj.id
                    }

                    vote = session.vote_storage.set_vote(vote_data)

                    ballots = []

                    for ballot in parsed_vote['ballots']:
                        voter = self.storage.people_storage.get_or_add_person(
                            fix_name(ballot['name'])
                        )

                        temp_ballot = {
                            'vote': vote['id'],
                            'option': ballot['option'],
                            'personvoter': voter.id
                            }
                        ballots.append(temp_ballot)
                    session.vote_storage.set_ballots(ballots)
                elif self.update:
                    logger.debug('UPDATE VOTE')
                    vote_data = {
                        'name': name
                    }
                    raise NotImplementedError('Update vote')
                    #vote = session.vote_storage.patch_vote(vote_id, vote_data)
                else:
                    print('Vote is allredy parsed')

    def find_epa(self, line):
        epas = None
        for m in re.finditer('broj:', line):
            m.start()
            epa_str = line[m.end():].strip()
            if '- ' in epa_str:
                epa_str = epa_str.replace('- ', '-')
            epa = epa_str.split(' ')
            if epas:
                epas = epas + '|' +epa[0]
            else:
                epas = epa[0]
        return epas

    def get_session_type(self, name):
        if 'hitra' in name:
            return 'urgent'
        else:
            return 'regular'


class get_PDF(object):
    def __init__(self, url, file_name):
        response = requests.get(url)
        import os
        cwd = os.getcwd()
        print(cwd)

        with open('files/'+file_name, 'wb') as f:
            f.write(response.content)

        with open('files/'+file_name, "rb") as f:
            self.pdf = pdftotext.PDF(f)

class LegislationParser(get_PDF):
    def __init__(self, obj):
        logger.debug('init')
        super().__init__(obj['url'], obj['file_name'])
        #response = requests.get(obj['url'])

        logger.debug(self.pdf)
        logger.debug('pdf')

        content = "".join(self.pdf)
        logger.debug(content)
        self.content = content.replace('\uf0b7', '').split('\n')
        self.state = 'meta'
        self.legislation = []

        self.rejected_words = ['ODBIJEN PRIJEDLOG ZAKONA', 'NIJE USVOJEN PRIJEDLOG ZAKONA']
        self.in_procedure_words = ['PRIJEDLOG ZAKONA', 'UPUĆEN', "PRIJEDLOGU ZAKONA", "USVOJEN ZAHTJEV ZA HITNI POSTUPAK", "NIJE USVOJEN ZAHTJEV ZA HITNI POSTUPAK"]
        self.adopted_enacted_words = ['USVOJEN ZAKON', 'USVOJEN PRIJEDLOG ZAKONA']
        self.suspended_words = ['ZAKONODAVNI POSTUPAK OBUSTAVLJEN']

        self.skip_table_row_if_contains = ['DELEGATSKA INICIJATIVA', 'IZVJEŠTAJ', 'SAGLASNOST', 'ZNANJU INFORMACIJA', 'POSLANIČKA INICIJATIVA']

        self.legislation = self.parse()
        logger.debug(self.legislation)

    def if_string_contains_any(self, input_string, substrings):
        return any(substring in input_string for substring in substrings)
    
    def if_string_contains_all(self, input_string, substrings):
        return all(substring in input_string for substring in substrings)

    def get_results(self, house):
        find_epa = r'[- 0-9]*\d{3}\/\d{2}'

        output = []

        for law in self.legislation:
            epa = re.findall(find_epa, law['text'])
            if self.if_string_contains_any(law['result'], self.skip_table_row_if_contains):
                logger.debug('skip reason:  DELEGATSKA INICIJATIVA IZVJEŠTAJ SAGLASNOST ZNANJU INFORMACIJA')
                continue
            if epa and 'zakon' in law['text'].lower():
                result = ''
                if self.if_string_contains_any(law['result'], self.rejected_words):
                    result = 'rejected'
                if self.if_string_contains_any(law['result'], self.suspended_words):
                    result = 'suspended'
                elif self.if_string_contains_any(law['result'], self.adopted_enacted_words):
                    if house == 'Dom naroda':
                        if 'U PRVOM ČITANJU' in law['result']:
                            result = 'adopted'
                        else:
                            result = 'enacted'

                    elif house == 'Predstavnički dom':
                        result = 'in_procedure'
                elif self.if_string_contains_any(law['result'], self.in_procedure_words):
                    result = 'in_procedure'
                else:
                    # IF theres unknown result text then dont add it to output
                    logger.debug('skip IF theres unknown result text then dont add it to output')
                    continue
                output.append({
                    'epa': epa[0].replace(' ', ''),
                    'text': law['text'],
                    'result_text': law['result'],
                    'result': result
                })
        return output

    def parse(self):
        start_of_agenda_no = r'^\d*\.[ \s]+[a-zžćčšđA-ZŽĆČĐŠ]*'
        agenda_items = []

        text = []
        result = []

        for line in self.content:
            line_columns = re.split("\s\s+", line.strip())

            if self.state == 'meta':
                if re.findall(start_of_agenda_no, line):
                    self.state = 'parse'
            if self.state == 'parse':
                # new line
                if re.findall(start_of_agenda_no, line):
                    # new agenda item

                    # append previous
                    if text and result:
                        agenda_items.append({
                            'text': ' '.join(text),
                            'result': ' '.join(result)
                        })

                    line_columns = re.split("\s\s+", re.split("^\d+. ", line)[1])
                    line_columns = [x for x in line_columns if x]
                    leading_spaces = len(line)-len(line.lstrip())
                    if len(line_columns) == 1:
                        if leading_spaces > 10:
                            text = []
                            result = [line_columns[0]]
                        else:
                            text = [line_columns[0]]
                            result = []
                    else:
                        text = [line_columns[0]]
                        result = [line_columns[1]]
                else:
                    # append line
                    leading_spaces = len(line)-len(line.lstrip())
                    if leading_spaces > 10: # if second column has more rows than first
                        result.append(line_columns[0])
                    else:
                        text.append(line_columns[0])
                        if len(line_columns) == 2:
                            result.append(line_columns[1])

        agenda_items.append({
            'text': ' '.join(text),
            'result': ' '.join(result)
        })
        return agenda_items


class ContentParser(get_PDF):
    def __init__(self, obj):
        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)
        self.content = content.split('\n')
        self.state = 'start'
        self.speeches = []

        self.parse()

    def parse(self):
        current_speaker = ''
        current_content = []
        for line in self.content:
            #logger.debug(line)
            line = line.strip()
            if self.state == 'start':
                if line in ['PREDSJEDAVAJUĆI', 'PREDSJEDATELJICA', 'PREDSJEDATELJ']:
                    self.state = 'parse'
                    continue
            elif self.state == 'parse':
                # skip line if line is not speakers content
                if not line or line[0]=='/' or '___(?)' in line or line.isdigit() or 'Sjednica završena' in line:
                    continue
                # line is of new speaker name
                if line.isupper():
                    if current_content:
                        self.speeches.append({
                            'speaker': current_speaker,
                            'content': ' '.join(current_content),
                        })
                        current_content = []
                    current_speaker = line
                # parse content
                else:
                    current_content.append(line)
        self.speeches.append({
            'speaker': current_speaker,
            'content': ' '.join(current_content),
        })



class VotesParser(get_PDF):
    def __init__(self, obj):
        self.VOTE_MAP = {'Protiv': 'against', 'Za': 'for', 'Nije glasao': 'abstain', 'Suzdržan': 'abstain', 'Nije prisutan': 'absent'}

        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)

        self.content = content.split('\n')
        self.state = 'start'
        self.votes = []
        self.curr_title = ''

        self.parse()

        #logger.debug(self.votes)

    def merge_name(self, name, agenda, typ):
        return ' - '.join([i for i in [name, agenda, typ] if i])

    def parse(self):
        current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}

        # helpers for find agenda
        self.num_of_lines = 0
        self.found_keyword = False

        for line in self.content:
            logger.debug(line)
            logger.debug(self.state)
            #logger.debug(self.state, self.num_of_lines, self.found_keyword)
            line = line.strip()
            if re.split("\s\s+", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN NIJE PRISUTAN', 'UKUPNO'] or re.split("\s\s+", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN', 'NIJE PRISUTAN', 'UKUPNO']:
                logger.debug("\n New VOTE \n")
                self.state = 'start'
                current_vote['name'] = ' '.join(current_vote['name'])
                current_vote['name'] = self.merge_name(current_vote['name'], ' '.join(current_vote['agenda_item_name']), current_vote.get('type', ''))
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                logger.debug(current_vote['name'])
                if current_vote['ballots']:
                    self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': []}
                continue

            if self.state == 'start':
                if line.startswith('Redni broj glasanja'):
                    self.state = 'parse'
                    continue

            elif self.state == 'agenda-disable':
                current_vote['agenda_item_name'].append(self.parse_multiline(line, self.curr_title, 'voteing-about'))
                if not self.num_of_lines:
                    self.state = 'voteing-about'

            # try it dirty
            elif self.state == 'agenda':
                if line.startswith('Tip glasanja:'):
                    self.state = 'parse'
                else:
                    line = line.replace('Glasanje o:', '').strip()
                    line = line.replace('7DþND\x03GQHYQRJ\x03UHGD\x1d', '').strip()
                    line = line.replace('Tačka dnevnog reda:', '').strip()
                    if sum(1 for c in line if c.isupper()) > len(line)/2:
                        line = decode_ba_string(line, 29)
                    current_vote['agenda_item_name'].append(line)

            elif self.state == 'voteing-about':
                if line.isupper():
                    line = decode_ba_string(line, 29)
                current_vote['name'].append(self.parse_multiline(line, 'Glasanje o:', 'parse'))



            logger.debug(self.curr_title)
            if self.state == 'parse':
                if line.startswith('Redni broj tačke'):
                    current_vote['agenda_number'] = line.split(':')[1].strip()
                    self.state = 'agenda'
                    logger.debug("AGENDA-NORMAL")
                    self.curr_title = 'Redni broj tačke'
                    self.num_of_lines = 0
                    self.found_keyword = False
                    continue

                if line.startswith('5HGQL\x03EURM\x03WDþNH\x1d'):
                    current_vote['agenda_number'] = line.replace('5HGQL\x03EURM\x03WDþNH\x1d', '').strip()
                    self.state = 'agenda'
                    logger.debug("AGENDA")
                    self.curr_title = '5HGQL\x03EURM\x03WDþNH\x1d'
                    self.num_of_lines = 0
                    self.found_keyword = False
                    continue
                if line.startswith('5HGQLEURMWDþNH'):
                    current_vote['agenda_number'] = line.replace('5HGQLEURMWDþNH', '').strip()
                    self.state = 'agenda'
                    logger.debug("AGENDA")
                    self.curr_title = '5HGQLEURMWDþNH'
                    self.num_of_lines = 0
                    self.found_keyword = False
                    continue
                if line.startswith('Datum i vrijeme glasanja'):
                    current_vote['start_time'] = datetime.strptime(line.split(':', 1)[1].strip(), API_DATE_FORMAT + '. %H:%M')
                #if line.startswith('Glasanje o'):
                #    current_vote['name'] = line.split(':')[1].strip()
                if line.startswith('Tip glasanja'):
                    if 'Poništeno' in line:
                        # skip this vote because it's repeted
                        current_vote = {'count': {}, 'ballots': [], 'agenda_item_name': [], 'name': []}
                        self.state = 'start'
                    else:
                        current_vote['type'] = line.split(':')[1].strip()
                if line.startswith('Prisutan'):
                    continue
                if line.startswith('Nije prisutan'):
                    current_vote['count']['absent'] = int(line[-5:].strip())
                if line.startswith('ZA'):
                    #current_vote['count']['for'] = int(line[-5:].strip())
                    pass
                if line.startswith('PROTIV'):
                    current_vote['count']['against'] = int(line[-5:].strip())
                if line.startswith('SUZDRŽAN'):
                    current_vote['count']['abstain'] = int(line[-5:].strip())
                if line and line[0].isdigit():
                    # parse ballot
                    #logger.debug(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})\.', line))
                    if line.split(' ')[0].endswith('.') and not bool(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})', line)):
                        #logger.debug("in", bool(re.match(r'(\d{1,2})\. (\d{1,2})\. (\d{4})\.', line)))
                        bb=self.parse_ballot(line)
                        if bb:
                            current_vote['ballots'].append(bb)
                if line.startswith('Tačka dnevnog reda:'):
                    self.state = 'agenda'
                    self.curr_title = 'Tačka dnevnog reda:'
                    current_vote['agenda_item_name'].append(line.replace('Tačka dnevnog reda:', '').strip())
                if line.startswith('7DþND\x03GQHYQRJ\x03UHGD\x1d'):
                    self.state = 'agenda'
                    self.curr_title = '7DþND\x03GQHYQRJ\x03UHGD\x1d'
                    current_vote['agenda_item_name'].append(decode_ba_string(line.replace('7DþND\x03GQHYQRJ\x03UHGD\x1d', '').strip(), 29))

    def parse_ballot(self, line):
        #logger.debug(repr(line))
        #logger.debug(line)
        try:
            temp1, name, temp2, option = re.split("\s\s+", line)
        except Exception as e:
            logger.debug(e)
            logger.debug(line)
            #raise Exception
            return {}
        return {'name': name, 'option': self.VOTE_MAP[option]}

    def parse_multiline(self, line, keyword, next_state):
        if line.startswith(keyword):
            # If is single line return end, else return switch for invert counter
            if self.num_of_lines:
                self.found_keyword = True
            else:
                self.state = next_state
            return line.replace(keyword, '').strip()
        else:
            if self.found_keyword:
                self.num_of_lines-=1
            else:
                self.num_of_lines+=1
            if not self.num_of_lines:
                self.state = next_state
                self.found_keyword = False
            return line.strip()


class VotesParserPeople(get_PDF):
    def __init__(self, obj):
        self.VOTE_MAP = {'PROTIV': 'against', 'ZA': 'for', 'NIJE PRISUTAN': 'absent', 'SUZDRŽAN': 'abstain'}

        super().__init__(obj['url'], obj['file_name'])
        response = requests.get(obj['url'])

        content = "".join(self.pdf)

        self.content = content.split('\n')
        self.state = 'start'
        self.votes = []

        self.parse()

        logger.debug(self.votes)

    def merge_name(self, name, agenda, typ):
        return ' - '.join([i for i in [name, agenda, typ] if i])

    def parse(self):
        current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': [], 'agenda-name': []}

        # helpers for find agenda
        self.num_of_lines = 0
        self.found_keyword = False

        for line in self.content:
            line = line.strip()
            if re.split("\s\s*", line.strip()) == ['ZA', 'PROTIV', 'SUZDRŽAN', 'NIJE', 'PRISUTAN', 'UKUPNO']:
                #logger.debug(line)
                #logger.debug(re.split("\s\s*", line.strip()))
                #logger.debug(re.split("\s\s+", line.strip()))
                self.state = 'start'
                current_vote['agenda_item_name'] = ' '.join(current_vote['agenda_item_name'])
                if current_vote['agenda_item_name'].endswith(";") or current_vote['agenda_item_name'].endswith(":"):
                    current_vote['agenda_item_name'] = current_vote['agenda_item_name'][0:-1]
                current_vote['name'] = ' '.join(current_vote['name'])
                if current_vote['name'].endswith(";") or current_vote['name'].endswith(":"):
                    current_vote['name'] = current_vote['name'][0:-1]
                #current_vote['name'] = ' '.join(current_vote['name'])

                current_vote['name'] = self.merge_name(current_vote['name'], ' '.join(current_vote['agenda-name']), current_vote.get('type', ''))
                logger.debug(current_vote['name'])

                if current_vote['ballots']:
                    self.votes.append(current_vote)
                current_vote = {'count':{}, 'ballots':[], 'agenda_item_name':[], 'name': [], 'agenda-name': []}
                continue

            if self.state == 'start':
                logger.debug('start')
                if line.startswith('Rezultati glasanja'):
                    self.state = 'date'
                    continue

            elif self.state == 'date':
                logger.debug('date')
                try:
                    current_vote['start_time'] = datetime.strptime(line, API_DATE_FORMAT + ' %H:%M:%S')
                except Exception as e:
                    print(e)
                    print(line)
                    continue
                self.state = 'agenda'
                continue

            elif self.state == 'agenda':
                logger.debug('agenda')
                if line.startswith('Dom:') or line.startswith('Sjednica:') or line.startswith('Način glasanja:') or line.startswith('1DþLQJODVDQMD'):
                    continue
                if line.startswith('Redni broj:'):
                    line = line.replace("Redni broj:", "").strip()
                    current_vote['agenda_item_name'].append(line)
                if line.startswith('Redni broj glasanja: '):
                    line = line.replace("Redni broj glasanja: ", "").strip()
                    current_vote['agenda_item_name'].append(line)
                if line.startswith('Redni broj'):
                    line = line.replace("Redni broj", "").strip()
                    current_vote['agenda_item_name'].append(line)
                elif line.startswith('Glasanje o:'):
                    self.state = 'voteing-about'
                elif line.startswith('Naziv tačke:'):
                    self.state = 'agenda-name'
                else:
                    current_vote['agenda_item_name'].append(line.strip())

            if self.state == 'agenda-name':
                logger.debug('agenda-name')
                if line.startswith('Glasanje o:'):
                    self.state = 'voteing-about'
                else:
                    current_vote['agenda-name'].append(line.replace('Naziv tačke:', '').strip())

            if self.state == 'voteing-about':
                logger.debug('voting-about')
                if line.startswith('Tip glasanja:'):
                    if 'poništeno' in line:
                        logger.debug('ponisteno')
                        # skip this vote because it's repeted
                        current_vote = {'count': {}, 'ballots': [], 'agenda_item_name': [], 'agenda-name': [], 'name': []}
                        self.state = 'start'
                        continue
                    current_vote['type'] = line.replace('Tip glasanja:', '').strip()
                    self.state = 'parse'
                    continue
                current_vote['name'].append(line.replace('Glasanje o:', '').strip())

            if self.state == 'parse':
                logger.debug('parse')
                logger.debug(line)
                if line.startswith('Prisutno'):
                    current_vote['count']['absent'] = 15 - int(line[-5:].strip())
                elif line.startswith('ZA'):
                    current_vote['count']['for'] = int(line[-5:].strip())
                elif line.startswith('PROTIV'):
                    current_vote['count']['against'] = int(line[-5:].strip())
                elif line.startswith('SUZDRŽAN'):
                    current_vote['count']['abstain'] = int(line[-5:].strip())
                elif line.startswith('Ukupno'):
                    pass
                else:
                    # parse ballot
                    ballot = self.parse_ballot(line)
                    if ballot:
                        current_vote['ballots'].append(ballot)

    def parse_ballot(self, line):
        try:
            name, temp2, option = re.split("\s\s+", line)
        except Exception as e:
            print(line)
            print(e)
            return {}
        return {'name': name, 'option': self.VOTE_MAP[option]}
