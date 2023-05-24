from parse_utils.parladata_api import ParladataApi
from parse_utils.storage.vote_storage import VoteStorage


class PublicQuestion(object):
    def __init__(self, gov_id, id, is_new) -> None:
        # public question members
        self.id = id
        self.gov_id = gov_id
        self.is_new = is_new

    def get_key(self) -> str:
        return self.gov_id.strip().lower()

    @classmethod
    def get_key_from_dict(ctl, question) -> str:
        return question['gov_id'].strip().lower()


class PublicAnswer(object):
    def __init__(self, gov_id, id, is_new) -> None:
        # public answer members
        self.id = id
        self.gov_id = gov_id
        self.is_new = is_new

    def get_key(self) -> str:
        return self.gov_id.strip().lower()

    @classmethod
    def get_key_from_dict(ctl, answer) -> str:
        return answer['gov_id'].strip().lower()


class PublicQuestionStorage(object):
    def __init__(self, core_storage) -> None:
        self.parladata_api = ParladataApi()
        self.public_questions = {}
        self.public_answers = {}
        self.storage = core_storage

    def load_data(self):
        if not self.public_questions:
            for public_question in self.parladata_api.get_public_questions(mandate=self.storage.mandate_id):
                self.store_public_question(public_question, False)
            print(f'laoded was {len(self.public_questions)} public questions')
        if not self.public_answers:
            for public_answer in self.parladata_api.get_public_answers(mandate=self.storage.mandate_id):
                self.store_public_answer(public_answer, False)
            print(f'laoded was {len(self.public_answers)} public ansers')

    def store_public_question(self, public_question, is_new) -> PublicQuestion:
        temp_question = PublicQuestion(
            gov_id=public_question['gov_id'],
            id=public_question['id'],
            is_new=is_new,
        )
        self.public_questions[temp_question.get_key()] = temp_question
        return temp_question

    def store_public_answer(self, public_answer, is_new) -> PublicAnswer:
        temp_answer = PublicQuestion(
            gov_id=public_answer['gov_id'],
            id=public_answer['id'],
            is_new=is_new,
        )
        self.public_questions[temp_answer.get_key()] = temp_answer
        return temp_answer

    def set_public_question(self, data):
        added_question = self.parladata_api.set_public_question(data)
        self.store_public_question(added_question, True)
        return added_question

    def check_if_public_question_is_parsed(self, question):
        key = PublicQuestion.get_key_from_dict(question)
        return key in self.public_questions.keys()

    def get_public_question(self, gov_id):
        return self.public_questions[gov_id]

    def set_public_answer(self, data):
        added_answer = self.parladata_api.set_public_answer(data)
        self.store_public_answer(added_answer, True)
        return added_answer

    def check_if_public_answer_is_parsed(self, answer):
        key = PublicAnswer.get_key_from_dict(answer)
        return key in self.public_answers.keys()
