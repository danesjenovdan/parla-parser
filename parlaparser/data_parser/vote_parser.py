from parlaparser.data_parser.base_parser import BaseParser
from parlaparser.data_parser.utils import get_vote_key
from parlaparser.settings import API_URL, API_DATE_FORMAT
from datetime import datetime
import requests, re, json, pdftotext

PARSE_JUST_NEW_VOTES = True
FORCE_SET_DOCS = False

options_map = {
    'donesen':'enacted',
    'dostavljeno radi informiranja':'submitted',
    'odbijen':'rejected',
    'povučen':'retracted',
    'prihvaćen':'adopted',
    'prima se na znanje':'received',
    'u proceduri':'in_procedure'
}

options = {
    'za':'for',
    'protiv':'against',
    'suzdržan':'abstain',
    'suzdržana':'abstain',
    'suzdržanim':'abstain',
    'suzdržanih':'abstain',
    'susdržan':'abstain',
    'sudržan':'abstain',
    'suzdržani':'abstain',
    'suzdran':'abstain'
}

all_options = [
    'for',
    'against',
    'abstain',
    'absent'
]

class BallotsParser(BaseParser):
    options = {
        'za':'for',
        'protiv':'against',
        'suzdržan':'abstain',
        'suzdržana':'abstain',
        'suzdržanim':'abstain',
        'suzdržanih':'abstain',
        'susdržan':'abstain',
        'sudržan':'abstain',
        'suzdržani':'abstain',
        'suzdran':'abstain'
    }
    def __init__(self, data, reference):
        super(BallotsParser, self).__init__(reference)

        self.storage = reference.storage

        self.source_data = data
        self.title = data['title']
        self.url = data['url']
        self.docs = data['docs']
        self.session_name = data['session_name'].split('.')[0] + '. sjednica'
        try:
            date = datetime.strptime(data['date'], API_DATE_FORMAT + '.').isoformat()
        except:
            date = None

        session_data = {
            'organization':self.storage.main_org_id,
            'organizations':[self.storage.main_org_id],
            'in_review':False,
            'name':self.session_name,
            'start_time': date,
            'gov_id': data['session_name'].split('.')[0]
        }
        self.session = self.storage.session_storage.add_or_get_session(session_data)
        self.session.load_votes()
        self.motion_data = {
            'session': self.session.id
        }
        self.vote = {}
        self.act_data = {
            'status': self.storage.legislation_storage.get_legislation_status_by_name('in_procedure'),
            'result': None}
        self.time_f = None
        self.result_hirarhy = [
            'in_procedure',
            'rejected',
            'adopted',
            'enacted'
        ]
        self.act_result_options = ('rejected', 'adopted', 'adopted')
        self.parse_title()
        self.ballots = None
        self.act = None
        if data['type'] == 'vote':
            # vote without ballots
            try:
                self.parse_time_from_result_data()
            except Exception as e:
                    print("FAILLLLSSSS", e)
                    return
            if self.session.vote_storage.check_if_motion_is_parsed(self.motion_data):
                if PARSE_JUST_NEW_VOTES:
                    pass
                else:
                    # update vote / docs
                    self.parse_results_from_content()
                    try:
                        self.parse_time_from_result_data()
                        if FORCE_SET_DOCS:
                            print("set_docs")
                            self.set_docs()
                    except:
                        print("FAILLLLSSSS")
                        return
                    print("WOOHOOO")
            else:
                self.parse_results_from_content()
                self.set_data()
                self.set_docs()

        if data['type'] == 'vote_ballots':
            print('vote_ballots')
            self.time = data['time']
            self.ballots = data['ballots']
            self.parse_time()
            print("")
            if self.session.vote_storage.check_if_motion_is_parsed(self.motion_data):
                print('motion is saved')
                if self.is_motion_saved_without_ballots():
                    # TODO add ballots to vote
                    self.parse_results()
                    motion_id = self.reference.motions[self.source_data['id']]
                    vote_id = self.reference.votes_without_ballots[motion_id]
                    self.parse_ballots(vote_id)
                elif PARSE_JUST_NEW_VOTES:
                    print('This motion is allready parsed')
                else:
                    print('Update motion')
                    self.parse_results()
                    self.set_data()
                    self.set_docs()
            else:
                self.parse_results()
                self.set_data()
                self.set_docs()

        if data['type'] == 'legislation':
            self.save_legislation()


    def save_legislation(self):
        self.act_data['session'] = self.session.id
        self.act_data['procedure_ended'] = False
        self.act_data['status'] = self.storage.legislation_storage.get_legislation_status_by_name('in_procedure')
        self.act_data['result'] = False
        if 'date_to_procedure' in self.source_data.keys():
            d_time = datetime.strptime(self.source_data['date_to_procedure'], '%Y-%m-%dT%H:%M:%SZ')
        elif 'time' in self.source_data.keys():
            d_time = datetime.strptime(self.source_data['time'], '%d.%m.%Y. %H:%M')
        else:
            raise Exception("No time")
        self.act_data['date'] = d_time.isoformat()
        if self.act_data['classification'] == 'act':
            self.act_data['classification'] = self.storage.legislation_storage.legislation_classifications['act'].id
            #self.act = self.add_or_update_act(self.act_data['text'], self.act_data)
            self.act = self.storage.legislation_storage.update_or_add_law(self.act_data)
        else:
            note = None
            for doc in self.docs:
                if doc['text'].lower().startswith('pz') or doc['text'].lower().startswith('pze'):
                    note = ContentParser(doc).parse()

            if note:
                self.act_data['note'] = ' '.join(note)
            self.act_data['classification'] = self.storage.legislation_storage.legislation_classifications['law'].id
            #self.act = self.add_or_update_law(self.act_data['epa'], self.act_data)
            self.act = self.storage.legislation_storage.update_or_add_law(self.act_data)

    def is_motion_saved(self):
        print('IS SAVED:  ', self.source_data['id'] in self.reference.motions.keys())
        return self.source_data['id'] in self.reference.motions.keys()

    def is_motion_saved_without_ballots(self):
        #return self.source_data['id'] in self.reference.votes_without_ballots.keys()
        # TODO save to motion if has annonymous ballots
        return False

    def get_motion_id(self):
        return self.reference.motions[self.source_data['id']]

    def get_vote_id(self):
        return self.reference.votes[get_vote_key(self.vote['name'], self.vote['start_time'])]

    def get_line_id(self, line_ids):
        if line_ids:
            if self.source_data['type'] == 'vote_ballots':
                offset = len(line_ids) - self.source_data['m_items']
                return line_ids[(self.source_data['c_item'] + offset)]
            return line_ids[(-1)]
        else:
            return

    def parse_results_from_content(self):
        find_results = r'\(?(?P<number>\d+)\)?\s?(glas\w* )?[„\"]? ?(za|protiv|su[zs]?dr[zž]?an\w*)[“\"]?'
        self.counters = {}
        self.result = None
        match = None
        if self.source_data['results_data']:
            for paragraph in self.source_data['results_data']:
                matches = re.finditer(find_results, paragraph, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    votes = int(match.group(1))
                    option = match.group(3)
                    if votes:
                        if option:
                            if option in ('preferencijalna', 'odlučio', 'jedno', 'većinom',
                                          'zastupnika'):
                                print(paragraph)
                                break
                        option = options[option.lower()]
                        self.counters.update({option: votes})
                        option = None
                        votes = None

                if match:
                    self.result = self.find_result(paragraph)
                    if self.counters:
                        break
                #match = None

            if self.counters:
                self.counters.update(absent=(151 - sum(self.counters.values())))
                for opt in all_options:
                    if opt not in self.counters:
                        self.counters.update({opt: 0})

                self.vote['counter'] = json.dumps(self.counters)
            self.vote['result'] = self.result
            self.motion_data['result'] = self.result
            if self.result:
                if self.act_data['procedure'] in ['drugo čitanje', 'hitni postupak']:
                    self.act_data['result'] = self.act_result_options[int(self.result)]
                else:
                    self.act_data['result'] = self.act_result_options[0 if int(self.result) == 0 else 2]
            print(self.counters, 'result:', self.result)

    def find_result(self, text):
        negative_words = [
         'ne prihvaća',
         'nije podržao',
         'da ne prihvati',
         'ne podupire donošenje',
         'nije mogao utvrditi',
         'nije donesen',
         'nije dobio']
        positive_words = [
         'odlučio predložiti',
         'da donese',
         'donošenje',
         'je prihvaćeno'
         'podržao',
         'prihvati',
         'je donesen',
         'je donesenpredložiti',
         'većinom glasova',
         'je donesena',
         'da se prihvaća']
        for word in negative_words:
            if word in text:
                return '0'

        for word in positive_words:
            if word in text:
                return '1'

    def parse_results(self):
        if self.source_data['for_count'] > self.source_data['against_count']:
            self.vote['result'] = 1
            self.motion_data['result'] = 1
            self.act_data['result'] = self.act_result_options[1]
        else:
            self.vote['result'] = 0
            self.motion_data['result'] = 0
            self.act_data['result'] = self.act_result_options[0]
        self.act_data['procedure_phase'] = self.act_data['result']
        self.act_data['status'] = self.storage.legislation_storage.get_legislation_status_by_name(self.act_data['result'])

    def parse_time(self):
        self.time_f = datetime.strptime(self.time, '%d.%m.%Y. %H:%M')
        self.motion_data['datetime'] = self.time_f.isoformat()
        self.vote['timestamp'] = self.time_f.isoformat()
        self.act_data['timestamp'] = self.time_f.isoformat()

    def parse_title(self):
        text = self.title.lower()
        if text[-1] == ';':
            text = text[:-1]

        self.act_data['text'] = text
        self.motion_data['text'] = text
        self.motion_data['title'] = text
        self.motion_data['gov_id'] = self.source_data['id']
        self.vote['name'] = text
        epa = self.find_epa_in_name(self.title)
        if epa:
            self.vote['epa'] = epa
            self.motion_data['epa'] = epa
            self.act_data['epa'] = epa
            self.act_data['classification'] = 'zakon'
            if ', hitni postupak' in text:
                text = text.split(', hitni postupak')[0]
                self.act_result_options = ('rejected', 'enacted', 'adopted')
                self.act_data['procedure'] = 'hitni postupak'
                self.act_data['procedure_ended'] = True
            else:
                if ', drugo čitanje' in text:
                    text = text.split(', drugo čitanje')[0]
                    self.act_result_options = ('rejected', 'enacted')
                    self.act_data['procedure'] = 'drugo čitanje'
                    self.act_data['procedure_ended'] = True
                else:
                    if ', prvo čitanje' in text:
                        text = text.split(', prvo čitanje')[0]
                        self.act_result_options = ('rejected', 'adopted', 'adopted')
                        self.act_data['procedure'] = 'prvo čitanje'
            self.act_data['text'] = text
        else:
            self.act_data['classification'] = 'act'
            self.act_data['epa'] = 'act' + self.url.split('=')[(-1)]
            self.vote['epa'] = self.act_data['epa']
            self.motion_data['epa'] = self.act_data['epa']
            if '- podnositelj' in text:
                self.act_data['text'] = text.split('- podnositelj')[0].strip()
            else:
                if '- predlagatelj' in text:
                    self.act_data['text'] = text.split('- predlagatelj')[0].strip()
                else:
                    self.act_data['text'] = text.strip()
            self.act_data['procedure_ended'] = True
            self.act_data['procedure'] = 'act'
        self.act_result_options = ('rejected', 'enacted', 'adopted')

    def parse_ballots(self, vote):
        option_map = {
            'abstained':'abstain',
            'for':'for',
            'against':'against'}
        data = []
        for ballot in self.ballots:
            person = self.storage.people_storage.get_or_add_person(ballot['voter'])
            option = option_map[ballot['option']]
            temp = {
                'option': option,
                'vote': vote,
                'personvoter': person.id,
            }
            data.append(temp)

        self.session.vote_storage.set_ballots(data)

    def add_anonymous_ballots(self, vote):
        data = []
        for option, count in self.counters.items():
            for i in range(count):
                temp = {
                    'option': option,
                    'vote': vote,
                    'voter': None,
                }
                data.append(temp)
        self.session.vote_storage.set_ballots(data)


    def set_data(self):
        self.save_legislation()

        self.motion = self.session.vote_storage.add_or_get_motion_and_vote(self.motion_data)


        if self.ballots:
            self.parse_ballots(self.motion.vote.id)
        elif self.counters:
            self.add_anonymous_ballots(self.motion.vote.id)

    def set_docs(self):
        if self.motion.is_new or FORCE_SET_DOCS:
            for doc in self.docs:
                data = {
                    'url': doc['url'],
                    'name': doc['text'],
                    'motion': self.motion.id
                }
                self.storage.set_link(data)

    def parse_time_from_result_data(self):
        time = datetime.strptime(self.source_data['date'], API_DATE_FORMAT + '.')
        self.time_f = time
        self.motion_data['datetime'] = time.isoformat()
        self.vote['timestamp'] = time.isoformat()
        self.act_data['timestamp'] = time.isoformat()

    def parse_non_balots_balots(self, data):
        opt_map = {
            'suzdržana':'abstain',
            'za':'for',
            'protiv':'against'}
        r = re.compile('\\(.*\\)')
        text = self.results_data
        if len(text) > 1:
            if '(' in text[1]:
                data = r.searchtext[1].group(0)
            else:
                data = r.searchtext[0].group(0)
        else:
            data = data.replace('(', '').replace(')','').replace('\xa0',' ')
            splited = data.split(' ')
            j_data = {}
            if 'jednoglasno' in data:
                i = 3
                if splited[3] in ('glas', 'glasova'):
                    i = 4
                option = replace_nonalphanum(splited[i])
                votes = splited[1]
                j_data = {opt_map[option]: votes}
            else:
                votes = 0
                option = ''
                for token in splited:
                    token = replace_nonalphanum(token)
                    if token.isalpha:
                        if token in opt_map.keys():
                            option = token
                            j_data[opt_map[option]] = votes
                        if token.isdigit:
                            votes = int(token)

        self.vote['counter'] = json.dumps(j_data)

    def find_epa_in_name(self, name):
        search_epa = re.compile('(\\d+)')
        name = name.lower()
        if 'p.z.' in name:
            new_text = name.split('p.z.')[1]
            a = search_epa.search(new_text.strip())
            if a:
                return a.group(0)
        if 'p. z.' in name:
            new_text = name.split('p. z.')[1]
            a = search_epa.search(new_text.strip())
            if a:
                return a.group(0)

def replace_nonalphanum(word):
    word = re.sub('\\W+', '', word)
    return word


class Get_PDF(object):

    def __init__(self, url, file_name):
        response = requests.get((url), verify=False)
        with open('files/' + file_name, 'wb') as (f):
            f.write(response.content)
        with open('files/' + file_name, 'rb') as (f):
            self.pdf = pdftotext.PDF(f)


class ContentParser(Get_PDF):
    reg_roman = '(?=\\b[MCDXLVI]{1,6}\\b)M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'

    def __init__(self, obj):
        super().__init__(obj['url'], obj['text'])
        content = ''.join(self.pdf)
        self.content = content.split('\n')

    def parse(self):
        read = False
        out_data = []
        for line in self.content:
            if re.match(self.reg_roman, line.strip()):
                if 'OCJENA STANJA I OSNOVNA PITANJA' in line.upper():
                    read = True
                else:
                    read = False
            elif line.strip() == line.strip().upper():
                continue
            if read:
                out_data.append(line)

        print(out_data)
        return out_data


class ContentParserFILE(object):
    reg_roman = '(?=\\b[MCDXLVI]{1,6}\\b)M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'
    END_WORDS = [
     'Osnovna pitanja koja se uređuju predloženim Zakonom',
     'Posljedice koje će donošenjem zakona proisteći',
     'Pitanja koja se trebaju urediti Zakonom',
     'Posljedice koje će proisteći donošenjem Zakona',
     'Osnovna pitanja koja se trebaju urediti Zakonom',
     'Razlozi zbog kojih se Zakon donosi',
     'Osnovna pitanja koja se trebaju urediti ovim Zakonom',
     'Posljedice koje će proisteći donošenjem ovoga Zakona']
    SKIP_START_LINES = [
     'Ocjena stanja i pitanja koja se rješavaju ovim Zakonom',
     'Ocjena stanja']

    def __init__(self, file_name):
        with open(file_name, 'rb') as f:
            self.pdf = pdftotext.PDF(f)
        content = ''.join(self.pdf)
        self.content = content.split('\n')

    def parse(self):
        read = False
        out_data = []
        for line in self.content:
            if re.match(self.reg_roman, line.strip()):
                if 'OCJENA STANJA I OSNOVNA PITANJA' in line.upper():
                    read = True
                else:
                    if read == True:
                        if line.strip() == line.strip().upper():
                            break
                    read = False
            else:
                if 'Ocjena stanja' in line and len(line.strip().replace('Ocjena stanja', '').strip()) < 3:
                    continue
                else:
                    if self.check_end_inner(line):
                        break
                if line.strip() == line.strip().upper():
                    continue
            if read:
                out_data.append(line)

        print(out_data)
        return out_data

    def check_end_inner(self, line):
        for word in self.END_WORDS:
            print(len(line.strip().replace(word, '').strip()))
            if word in line and len(line.strip().replace(word, '').strip()) < 3:
                return True

        return False
