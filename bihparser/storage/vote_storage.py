from bihparser.storage.parladata_api import ParladataApi


class Motion(object):
    def __init__(self, id, text, title, session, datetime, gov_id, is_new) -> None:
        self.id = id
        #self.epa = epa
        self.text = text
        self.title = title
        self.session = session
        self.datetime = datetime
        self.gov_id = gov_id
        self.is_new = is_new

    def get_key(self) -> str:
        #return (self.gov_id if self.gov_id else '').strip().lower()
        return (self.text + '_' + self.datetime).strip().lower()

    @classmethod
    def get_key_from_dict(ctl, data) -> str:
        #return (data['gov_id'] if data['gov_id'] else '').strip().lower()
        return (data['text'] + '_' + data['datetime']).strip().lower()

class VoteStorage(object):
    def __init__(self, session) -> None:
        self.parladata_api = ParladataApi()
        self.motions = {}

        self.session = session

        for motion in self.parladata_api.get_motions(session=session.id):
            temp_motion =Motion(
                text=motion['text'],
                title=motion['title'],
                id=motion['id'],
                session=motion['session'],
                gov_id=motion['gov_id'],
                datetime = motion['datetime'],
                is_new=False,
            )
            self.motions[temp_motion.get_key()] = temp_motion

    def set_vote(self, data):
        added_vote = self.parladata_api.set_vote(data)
        return added_vote

    def patch_vote(self, vote, data):
        self.parladata_api.patch_vote(vote.id, data)

    def set_ballots(self, data):
        added_ballots = self.parladata_api.set_ballots(data)

    def set_motion(self, data):
        added_motion = self.parladata_api.set_motion(data)
        motion =Motion(
            text=added_motion['text'],
            title=added_motion['title'],
            id=added_motion['id'],
            session=added_motion['session'],
            gov_id=added_motion['gov_id'],
            datetime = added_motion['datetime'],
            is_new=False,
        )
        self.motions[motion.get_key()] = motion
        return motion

    def patch_motion(self, motion, data):
        self.parladata_api.patch_motion(motion.id, data)

    def check_if_motion_is_parsed(self, motion):
        key = Motion.get_key_from_dict(motion)
        return key in self.motions.keys()



