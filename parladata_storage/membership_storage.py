from parladata_storage.parladata_api import ParladataApi
from collections import defaultdict
from datetime import datetime


class Membership(object):
    def __init__(self, person_id, organization_id, on_behalf_of_id, role, start_time, end_time, mandate, id, is_new) -> None:
        self.parladata_api = ParladataApi()

        # question members
        self.id = id
        self.person_id = person_id
        self.organization_id = organization_id
        self.on_behalf_of_id = on_behalf_of_id
        self.role = role
        self.start_time = start_time
        self.end_time = end_time
        self.mandate = mandate
        self.is_new = is_new

    def get_key(self) -> str:
        return f'{self.person_id}_{self.organization_id}_{self.on_behalf_of_id}_{self.role}_{self.mandate}'

    @classmethod
    def get_key_from_dict(ctl, membership) -> str:
        return f'{membership["member"]}_{membership["organization"]}_{membership["on_behalf_of"]}_{membership["role"]}_{membership["mandate"]}'

    def set_end_time(self, end_time):
        self.end_time = end_time
        self.parladata_api.patch_memberships(self.id, {'end_time': end_time})


class MembershipStorage(object):
    def __init__(self, core_storage) -> None:
        self.parladata_api = ParladataApi()
        self.memberships = defaultdict(list)
        self.storage = core_storage

        self.temporary_data = defaultdict(list)
        self.temporary_roles = defaultdict(list)

        self.active_voters = defaultdict(dict)

        self.first_load = False

    def store_membership(self, membership, is_new) -> Membership:
        temp_membership = Membership(
            person_id=membership['member'],
            organization_id=membership['organization'],
            on_behalf_of_id=membership['on_behalf_of'],
            role=membership['role'],
            start_time=membership['start_time'],
            end_time=membership.get('end_time', None),
            mandate=membership['mandate'],
            id=membership['id'],
            is_new=is_new,
        )
        self.memberships[temp_membership.get_key()].append(temp_membership)
        person = self.storage.people_storage.get_person_by_id(membership['member'])
        organization = self.storage.organization_storage.get_organization_by_id(membership['organization'])

        if membership['organization'] == int(self.storage.main_org_id):
            if (membership.get('end_time', None) == None or membership['end_time'] > datetime.now().isoformat()) and membership['role'] == 'voter':
                self.active_voters[membership['member']][membership['on_behalf_of']] = temp_membership

        if person:
            person.memberships.append(temp_membership)
        if organization:
            organization.memberships.append(temp_membership)
        return temp_membership

    def load_data(self):
        if not self.memberships:
            for membership in self.parladata_api.get_memberships(mandate=self.storage.mandate_id):
                self.store_membership(membership, is_new=False)
            print(f'laoded was {len(self.memberships)} memberships')

        if not self.memberships:
            self.first_load = True

    def add_or_get_membership(self, data) -> Membership:
        key = Membership.get_key_from_dict(data)
        if key in self.memberships.keys():
            memberships = self.memberships[key]
            for membership in memberships:
                if not membership.end_time:
                    return membership

        membership = self.set_membership(data)

        return membership

    def set_membership(self, data):
        
        added_membership = self.parladata_api.set_membership(data)
        new_membership = self.store_membership(added_membership, is_new=True)
        return new_membership

    def check_if_membership_is_parsed(self, membership):
        key = Membership.get_key_from_dict(membership)
        return key in self.memberships.keys()
    
    def refresh_memberships(self):
        keep_memebrship_ids = []
        memberships_to_end = []

        for org_id, org_data in self.temporary_data.items():
            for single_org_membership in org_data:
                # TODO: set start time
                if self.first_load:
                    start_time = self.storage.mandate_start_time.isoformat()
                else:
                    start_time = datetime.now().isoformat()
                print(single_org_membership)
                if single_org_membership['organization']:
                    on_behalf_of = single_org_membership['organization'].id
                else:
                    # workaround for members without profile get organization from roles (organiaztion page)
                    on_behalf_of = self.get_members_organization_from_roles(single_org_membership['member'].id)
                    

                if single_org_membership['type'] == 'sabor':
                    stored_membership = self.add_or_get_membership(
                        {
                            'member': single_org_membership['member'].id,
                            'organization': org_id,
                            'role': 'voter',
                            'start_time': start_time,
                            'mandate': self.storage.mandate_id,
                            'on_behalf_of': on_behalf_of
                        }
                    )
                    keep_memebrship_ids.append(stored_membership.id)
                    if stored_membership.is_new:
                        # if stored new membership membership
                        person_voter_memberships = self.active_voters.get(single_org_membership['member'].id)
                        if person_voter_memberships and len(person_voter_memberships) > 1:
                            # person has change club
                            on_behalf_ofs = list(person_voter_memberships.keys())
                            on_behalf_ofs.remove(on_behalf_of)
                            memberships_to_end.append(person_voter_memberships[on_behalf_ofs[0]])
                        
                    if on_behalf_of:
                        role = self.get_members_role_in_organization(single_org_membership['member'].id, on_behalf_of)
                        print(role)
                    
                        self.add_or_get_membership(
                            {
                                'member': single_org_membership['member'].id,
                                'organization': on_behalf_of,
                                'role': role,
                                'start_time': start_time,
                                'mandate': self.storage.mandate_id,
                                'on_behalf_of': None
                            }
                        )
                elif single_org_membership['type'] == 'commitee':
                    if not str(org_id) == str(self.storage.main_org_id):
                        self.add_or_get_membership(
                            {
                                'member': single_org_membership['member'].id,
                                'organization': org_id,
                                'role': 'voter',
                                'start_time': start_time,
                                'mandate': self.storage.mandate_id,
                                'on_behalf_of': on_behalf_of
                            }
                        )

                    role = single_org_membership.get('role', 'member')
                    if on_behalf_of:
                        self.add_or_get_membership(
                            {
                                'member': single_org_membership['member'].id,
                                'organization': org_id,
                                'role': role,
                                'start_time': start_time,
                                'mandate': self.storage.mandate_id,
                                'on_behalf_of': on_behalf_of
                            }
                        )

        print("changed mambership", memberships_to_end)

        print(keep_memebrship_ids)
        # find memberships that are not parsed from sabor members
        for voter in self.active_voters.values():
            for voter_membership in voter.values():
                if voter_membership.id not in keep_memebrship_ids:
                    # end voter membership because it is not parsed from the sabor page
                    print(f"membership {voter_membership.id} of person with id {voter_membership.person_id} has to be end, role: {voter_membership.role}")
                    memberships_to_end.append(voter_membership)
                    if self.count_active_voter_membership(voter_membership.person_id) > 1:
                        # end just previous club membership
                        print("end just previous club membership")
                        memberships_to_end.append(voter_membership)
                        for mm in self.get_all_active_persons_memberships(voter_membership.person_id):
                            if (mm.organization_id == voter_membership.on_behalf_of_id) and mm.end_time == None:
                                memberships_to_end.append(mm)
                                print("end single membership")
                    else:
                        # end all person memberships
                        for mm in self.get_all_active_persons_memberships(voter_membership.person_id):
                            memberships_to_end.append(mm)
                            print("end all membership")
        
        end_time = datetime.now().isoformat()
        # end memberships that are not valid anymore
        for single_org_membership in memberships_to_end:
            
            single_org_membership.set_end_time(end_time)
            print('End membership', single_org_membership.id, end_time)

    def get_all_active_persons_memberships(self, person_id):
        return [membership for membership in self.storage.people_storage.get_person_by_id(person_id).memberships if not membership.end_time]

    def count_active_voter_membership(self, person_id):
        person = self.storage.people_storage.get_person_by_id(person_id)
        count = 0
        for membership in person.memberships:
            if membership.organization_id == int(self.storage.main_org_id) and not membership.end_time and membership.role == 'voter':
                count += 1
        return count
    
    def get_members_role_in_organization(self, member_id, organization):
        role = None
        print(organization, member_id)
        for person_role in self.temporary_roles[organization]:
            print(str(member_id), str(person_role['member'].id), person_role['role'])
            if str(member_id) == str(person_role['member'].id):
                role = person_role['role']
                print("FOUND")
                break
        return role
    
    def get_members_organization_from_roles(self, member_id):
        """
        This is used for users without profiles
        """
        role = None
        for org_id, members in self.temporary_roles.items():
            for person_role in members:
                if str(member_id) == str(person_role['member'].id):
                    role = person_role['role']
                    print("FOUND")
                    return org_id
        return None


# vse ki imajo 2 membershipa v saboru jim vse zaključi
