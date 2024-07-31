from parladata_storage.parladata_api import ParladataApi


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
        self.vote = None
        self.parladata_api = ParladataApi()

    def get_key(self) -> str:
        date = self.datetime#.split('T')[0]
        return (self.text + '_' + date).strip().lower()

    @classmethod
    def get_key_from_dict(ctl, data) -> str:
        date = data['datetime']#.split('T')[0]
        return (data['text'] + '_' + date).strip().lower()
    
    def patch(self, data):
        self.parladata_api.patch_motion(self.id, data)


class Vote(object):
    def __init__(self, id, name, timestamp, has_anonymous_ballots, is_new) -> None:
        self.id = id
        self.name = name
        self.timestamp = timestamp
        self.has_anonymous_ballots = has_anonymous_ballots
        self.is_new = is_new
        self.parladata_api = ParladataApi()

    def delete_ballots(self):
        self.parladata_api.delete_vote_ballots(self.id)

    def get_key(self) -> str:
        date = self.timestamp.split('T')[0]
        return (self.name + '_' + date).strip().lower()

    @classmethod
    def get_key_from_dict(ctl, data) -> str:
        date = data['timestamp'].split('T')[0]
        return (data['name'] + '_' + date).strip().lower()

class VoteStorage(object):
    def __init__(self, session) -> None:
        self.parladata_api = ParladataApi()
        self.motions = {}
        self.anonymous_motions = None

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
            
            vote_id = motion['vote'][0]
            vote = self.parladata_api.get_vote(vote_id)
            temp_vote = Vote(
                name=vote['name'],
                id=vote_id,
                timestamp = vote['timestamp'],
                has_anonymous_ballots=vote['has_anonymous_ballots'],
                is_new=False
            )
            temp_motion.vote = temp_vote
            self.motions[temp_motion.get_key()] = temp_motion


    def patch_vote(self, vote, data):
        self.parladata_api.patch_vote(vote.id, data)

    def set_ballots(self, data):
        self.parladata_api.set_ballots(data)

    def set_motion(self, data):
        added_motion = self.parladata_api.set_motion(data)
        motion =Motion(
            text=added_motion['text'],
            title=added_motion['title'],
            id=added_motion['id'],
            session=added_motion['session'],
            gov_id=added_motion['gov_id'],
            datetime = added_motion['datetime'],
            is_new=True,
        )
        self.motions[motion.get_key()] = motion

        return motion

    def set_vote(self, data, motion):
        added_vote = self.parladata_api.set_vote(data)
        vote = Vote(
            name=added_vote['name'],
            id=added_vote['id'],
            timestamp = added_vote['timestamp'],
            is_new=True
        )
        motion.vote = vote
        return vote


    def add_or_get_motion_and_vote(self, data):
        if self.check_if_motion_is_parsed(data):
            key = Motion.get_key_from_dict(data)
            return self.motions[key]
        else:
            motion = self.set_motion(data)
            data['timestamp'] = data['datetime']
            del data['datetime']
            data['motion'] = motion.id
            data['name'] = data['title']
            self.set_vote(data, motion)
            return motion

    def patch_motion(self, motion, data):
        self.parladata_api.patch_motion(motion.id, data)

    def check_if_motion_is_parsed(self, motion):
        key = Motion.get_key_from_dict(motion)
        return self.motions.get(key, None)



