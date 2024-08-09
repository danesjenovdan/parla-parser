from .base_parser import BaseParser

from datetime import datetime

class QuestionParser(BaseParser):
    def __init__(self, data, reference):
        # call init of parent object
        super(QuestionParser, self).__init__(reference)
        """
        {
            #"recipient": ["Plenkovi\u0107, Andrej / Predsjednik Vlade RH; "],
            #"field": ["Prestanak dru\u0161tava; "],
            #"link": ["../NewReports/GetReport.aspx?reportType=5&id=8561&pisaniOdgovor=False&opis=False"],
            #"date": ["11.4.2018."],
            #"author": ["Bulj, Miro (MOST)"],
            #"title": "Zastupni\u010dko pitanje ",
            #"typ": ["na 8. sjednici"],
            #"signature": [],
            X"ref": ["IX"]},

            send link
        """

        self.storage = reference.storage
        self.question_storage = reference.storage.question_storage

        # copy item to object
        self.author = data['author'][0]
        self.title = data['title']
        self.ref = data['ref'][0]
        self.date = data['date'][0]
        self.typ = data['typ'][0]
        self.recipient = data['recipient'][0]
        self.field = data['field'][0]
        self.signature = data['edoc_url'].split('=')[1]
        self.edoc_url = data['edoc_url']
        self.dialog = data.get('dialog', None)
        if data['link']:
            self.url = data['link'][0]
        else:
            self.url = None
        if data['answer_date']:
            self.answer_date = datetime.strptime(data['answer_date'][0], "%d.%m.%Y.")
        else:
            self.answer_date = None
        if data['answer']:
            self.answer = data['answer'][0]
        else:
            self.answer = None

        # prepere dictionarys for setters
        self.question = {
            'gov_id': self.signature,
            'type_of_question': 'question',
            'mandate': self.storage.mandate_id
        }
        self.link = {}
        self.date_f = None

        if self.question_storage.check_if_question_is_parsed(self.question):
            question = self.question_storage.add_or_get_object(self.question)
            if question.answer_timestamp:
                pass
            else:
                print(self.answer_date)
                if self.answer_date:
                    # Update answer with answer date
                    question.update_data({'answer_timestamp': self.answer_date.isoformat()})
        else:
            # parse data
            self.parse_time()
            self.parse_data()

    def parse_time(self):
        self.date_f = datetime.strptime(self.date, "%d.%m.%Y.")
        self.question['timestamp'] = self.date_f.isoformat()
        self.link['date'] = self.date_f.strftime("%Y-%m-%d")

        if self.answer_date:
            self.question['answer_timestamp'] = self.answer_date.isoformat()

    def parse_data(self, update=False):
        if self.url:
            self.link['url'] = "http://edoc.sabor.hr/Views/" + self.url
            self.link['name'] = self.title

        self.question['signature'] = self.signature

        author_prs = []
        author_orgs = []
        authors = self.author.split(';')
        for author in authors:
            author_pr, author_org = self.parse_edoc_person(author)
            author_prs.append(author_pr)
            author_orgs.append(author_org)

        recipient_pr, recipient_org = self.parse_edoc_person(self.recipient)

        author_ids = []
        author_org_ids = []
        for author_pr in author_prs:
            author = self.storage.people_storage.get_or_add_object({"name": author_pr})
            author_ids.append(author.id)

        recipient = self.storage.people_storage.get_or_add_object({"name": recipient_pr})
        if recipient_org:
            recipient_party_id = self.storage.organization_storage.get_or_add_object({
                "name": recipient_org.strip()
            }).id
        else:
            recipient_party_id = None

        self.question['title'] = self.field + ' | ' + self.title
        answer = None

        if self.dialog:
            for line in self.dialog:
                author_pr, author_org = self.parse_edoc_person(line["speaker"])
                person_id = self.storage.people_storage.get_or_add_object({"name": author_pr}).id
                if person_id == author_ids[0]:
                   self.question['title'] = line["content"]
                if person_id == recipient.id:
                    answer = line["content"]
                    break

        self.question['person_authors'] = author_ids
        self.question['organization_authors'] = author_org_ids
        self.question['recipient_people'] = [recipient.id]
        if recipient_party_id:
            self.question['recipient_organizations'] = [recipient_party_id]
        self.question['recipient_text'] = self.recipient

        # send question
        question = self.question_storage.add_or_get_object(self.question)
        if answer:
            question.add_answer({
                "text": answer,
                "person_authors": [recipient.id],
                "timestamp": self.date_f.strftime("%Y-%m-%d")
            })

        # send link
        if question.is_new and self.url:
            self.link['question'] = question.id
            self.storage.set_link(self.link)
