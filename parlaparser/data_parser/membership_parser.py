from .base_parser import BaseParser

from ..settings import API_DATE_FORMAT

from datetime import datetime

"""
{
    "type": "club_roles",
    "club_name": "Klub zastupnica Centra, Gra\u0111ansko-liberalnog saveza i Stranke s imenom i prezimenom",
    "person_name": "Mrak-Tarita\u0161, Anka",
    "role": "\u010clanica"
},
{
    "type": "person",
    "name": "Dario Zurovec",
    "img_url": "https://www.sabor.hr/sites/default/files/uploads/sabor/2020-07-30/160101/Zurovec_Dario.jpeg",
    "club_role": null,
    "club_name": "Klub zastupnika Fokusa i Reformista",
    "commitees": [
        {
            "role": "\u010clan",
            "name": "Odbora za me\u0111uparlamentarnu suradnju",
            "start_date": "29.11.2022."
        }, {
            "role": "\u010clan",
            "name": "Izaslanstva Hrvatskoga sabora u Parlamentarnoj dimenziji Srednjoeuropske inicijative",
            "start_date": "29.11.2022."
        }
    ],
    "friendships": [
        "Albanija",
        "Al\u017eir",
        "Andora",
        "Argentina",
        "Armenija",
        "Australija",
        "Austrija",
        "Azerbajd\u017ean",
        "Belgija",
        "Bosna i Hercegovina",
        "Brazil",
        "Bugarska",
        "Crna Gora",
        "\u010ce\u0161ka",
        "\u010cile",
    ]
},
"""

ROLES = {
        "predsjednik": "president",
        "predsjednica": "president",
        "potpredsjednik": "deputy",
        "potpredsjednica": "deputy",
        "potpredsjednici": "deputy",
        "clanovi": "member",
        "članovi": "member",
        "\u010clanovi": "member",
        "članica": "member",
        "član": "member",
        "voditeljica": "leader",
        "voditelj": "leader",
        "president": "president",
        "deputy": "deputy",
        "member": "member",
    }

class ImageParser(BaseParser):
    def __init__(self, data, reference):
        super(ImageParser, self).__init__(reference)
        self.storage = reference.storage

        self.membership_storage = self.storage.membership_storage

        if data["type"] == "person":
            self.parse_person(data)

    def parse_person(self, data):
        person = self.storage.people_storage.get_or_add_object({
            "name": data["name"]
        })
        if data["img_url"]:
            person.save_image(data["img_url"])

class MembershipParser(BaseParser):
    def __init__(self, data, reference):
        super(MembershipParser, self).__init__(reference)
        self.storage = reference.storage

        self.membership_storage = self.storage.membership_storage

        if not self.membership_storage.memberships:
            self.membership_storage.load_data()

        if data["type"] == "person":
            self.parse_person(data)

        elif data["type"] == "club_roles":
            self.parse_club_roles(data)

        elif data["type"] == "refresh_memberships":
            self.refresh_memberships()

    def parse_person(self, data):
        person = self.storage.people_storage.get_or_add_object({
            "name": data["name"]
        })
        if data["club_name"]:
            club = self.storage.organization_storage.get_or_add_object({
                "name": data["club_name"]
            })
        else:
            club = None
        # self.membership_storage.temporary_data[self.storage.main_org_id].append({
        #     "is_voter": True,
        #     "member": person,
        #     "organization": club
        # })
        main_org = self.storage.organization_storage.get_organization_by_id(
            self.storage.main_org_id
        )
        self.membership_storage.per_person_data[person.id]["party"].append(
            {
                "is_voter": True,
                "member": person,
                "organization": main_org,
                "on_behalf_of": club,
                "role": "member",
                "type": "party",
                "mandate": self.storage.mandate_id,
            }
        )
        for commitee in data["commitees"]:
            commitee_org = self.storage.organization_storage.get_or_add_object({
                "name": commitee["name"]
            })
            # self.membership_storage.temporary_data[commitee_org.id].append({
            #     "type": "commitee",
            #     "member": person,
            #     "is_voter": True,
            #     "organization": commitee_org,
            #     "mandate": self.storage.mandate,
            #     "on_behalf_of": club,
            #     "start_date": datetime.strptime(commitee["start_date"], API_DATE_FORMAT + ".") if "start_time"  in commitee.keys() else None,
            #     "role": ROLES[commitee["role"].lower()] if "role" in commitee.keys() else "member"
            #     }
            # )
            self.membership_storage.per_person_data[person.id]["commitee"].append(
                {
                    "is_voter": True,
                    "member": person,
                    "organization": commitee_org,
                    "on_behalf_of": club,
                    "start_date": datetime.strptime(commitee["start_date"], API_DATE_FORMAT + ".") if "start_time"  in commitee.keys() else None,
                    "role": ROLES[commitee["role"].lower()] if "role" in commitee.keys() else "member",
                    "type": "commitee",
                    "mandate": self.storage.mandate_id,
                }
            )

    def prepare_data_structure(self):
        main_org = self.storage.organization_storage.get_organization_by_id(
            self.storage.main_org_id
        )

        for person_memberships in self.membership_storage.per_person_data.values():
            party = person_memberships.get("party", None)
            print(party)
            if party:
                party = party[0]
                try:
                    role = self.membership_storage.temporary_roles[party["member"].id][0]["role"]
                    party["role"] = role
                except IndexError:
                    pass
                if (
                    party["on_behalf_of"] and "Klub zastupnika nacionalnih manjina" in party["on_behalf_of"].name
                ):
                    party["on_behalf_of"] = None
                #party["on_behalf_of"] = party["organization"]
                #party["organization"] = main_org

        self.membership_storage.temporary_data = self.membership_storage.per_person_data
        self.membership_storage.temporary_roles = None


    def parse_club_roles(self, data):
        person_name = data["person_name"].strip()
        person = self.storage.people_storage.get_or_add_object({
            "name": person_name
        })
        club = self.storage.organization_storage.get_or_add_object({
            "name": data["club_name"].strip()
        })
        role = data["role"].lower()

        self.membership_storage.temporary_roles[person.id].append({
            'member': person,
            'organization': club,
            'role': ROLES[role]
        })

    def refresh_memberships(self):
        self.prepare_data_structure()
        self.membership_storage.refresh_per_person_memberships()
        
