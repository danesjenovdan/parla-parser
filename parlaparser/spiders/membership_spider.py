import scrapy
from datetime import datetime
import json, requests


class MembershipSpider(scrapy.Spider):
    name = "memberships"
    custom_settings = {
        "ITEM_PIPELINES": {"parlaparser.pipelines.ParlaparserPipeline": 1}
    }
    BASE_URL = "https://www.sabor.hr"
    start_urls = [
        "https://www.sabor.hr/hr/zastupnici",
        "https://sabor.hr/hr/zastupnici/klubovi-zastupnika",
    ]
    roles = {
        "Predsjednik": "president",
        "Predsjednica": "president",
        "Potpredsjednik": "deputy",
        "Potpredsjednica": "deputy",
        "Potpredsjednici": "deputy",
        "Članovi": "member",
    }

    def __init__(self, parse_memberships=False, parse_calendar=True, **kwargs):
        (super().__init__)(**kwargs)

    def parse(self, response):

        if response.css("h1::text").extract_first() == "Zastupnici u Saboru":
            data = {
                "view_name": "sabor_data",
                "view_display_id": "block_5",
                "field_saziv_target_id": "144984",
            }

            url = 'https://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax'

            for i in range(0,4):
                data["page"] = f"0,{i}"
                yield scrapy.FormRequest(url, callback=(self.parse_json), method='POST', formdata=data)
        else:
            for club in response.css("span.export-row-data>a"):
                url = club.css("::attr(href)").extract_first()
                yield scrapy.Request(
                    url=self.BASE_URL + url, callback=self.parse_club_page_roles, meta={"page": 0}
                )


    def parse_json(self, response):
        j_data = json.loads(response.css('textarea::text').extract_first())
        my_response = scrapy.selector.Selector(text=(j_data[4]['data'].strip()))
        
        for person_row in my_response.css("table>tbody>tr"):
            if person_row.css("td>a.no-link-list"):
                person_name = person_row.css("td>a::text").extract_first()
                person_name = person_name.split(", ")[1] + " " + person_name.split(", ")[0]
                yield {
                    "type": "person",
                    "name": person_name,
                    #"img_url": None,
                    "club_role": None,
                    "club_name": None,
                    "commitees": [],
                    "friendships": [],
                }
            else:
                person_page = person_row.css("td>a::attr(href)").extract_first()
                yield scrapy.Request(
                    url=self.BASE_URL + person_page,
                    callback=self.parse_person_page,
                    #meta={"club_name": name, "role": role},
                )
            
                


    def __parse__(self, response):
        """
        This parser starts from the clubs page and nezavisni zastupnici page
        """
        page_title = response.css("div>h1>div::text").extract_first()
        if page_title == "Nezavisni zastupnici":
            for person in response.css("div.views-field-field-prezime>div>a"):
                person_page = person.css("::attr(href)").extract_first().strip()

                yield scrapy.Request(
                    url=self.BASE_URL + person_page,
                    callback=self.parse_person_page,
                    meta={},
                )

        for club in response.css("span.export-row-data>a"):
            url = club.css("::attr(href)").extract_first()
            yield scrapy.Request(
                url=self.BASE_URL + url, callback=self.parse_club_page, meta={"page": 0}
            )

    def parse_club_page(self, response):
        current_page = response.meta.get("page", 0)
        name = response.css("h2.pre-title-second::text").extract_first()
        if name.strip() == "Klub zastupnika nacionalnih manjina":
            return

        content = response.css("div.sabor_data_entity")[0]
        for role_entry in content.css("div.views-element-container>div"):
            if role_entry.css(".klub-prethodni-clanovi"):
                # TODO return previous members for end memberships
                continue
            else:
                role = role_entry.css("h2.funkcija-naziv::text").extract_first().strip()
                if current_page > 0 and role != "Članovi":
                    # skip all roles except members on subsequent pages
                    continue
                entries = role_entry.css("div.row>div")
                for entry in entries:
                    person_page = entry.css("a::attr(href)").extract_first()
                    if person_page:
                        yield scrapy.Request(
                            url=self.BASE_URL + person_page.strip(),
                            callback=self.parse_person_page,
                            meta={"club_name": name, "role": role},
                        )
                    else:
                        person_name = entry.css("span.ime-prezime::text").extract_first().strip()
                        person_name = person_name.split(", ")[1] + " " + person_name.split(", ")[0]
                        yield {
                            "type": "person",
                            "name": person_name,
                            #"img_url": None,
                            "club_role": role,
                            "club_name": name,
                            "commitees": [],
                            "friendships": [],
                        }
        if response.css("li.pager__item.pager__item--last"):
            last_page_url = response.css(
                "li.pager__item.pager__item--last>a::attr(href)"
            ).extract_first()
            last_page = int(last_page_url.split("=")[1])

            if current_page < last_page:
                next_page = current_page + 1
                next_page_url = response.url.split("?")[0] + "?page=" + str(next_page)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_club_page,
                    meta={"page": next_page},
                )

    def parse_club_page_roles(self, response):
        current_page = response.meta.get("page", 0)
        name = response.css("h2.pre-title-second::text").extract_first()
        if name.strip() == "Klub zastupnika nacionalnih manjina":
            return

        content = response.css("div.sabor_data_entity")[0]
        for role_entry in content.css("div.views-element-container>div"):
            if role_entry.css(".klub-prethodni-clanovi"):
                # TODO return previous members for end memberships
                continue
            else:
                role = role_entry.css("h2.funkcija-naziv::text").extract_first().strip()

                if role.startswith("zamjen"):
                    # skip zamjenih memberships
                    continue

                if (current_page > 0) and not role.startswith("Član"):
                    # skip all roles except members on subsequent pages
                    continue
                entries = role_entry.css("div.row>div")
                for entry in entries:
                    person_name = entry.css("span.ime-prezime::text").extract_first().strip()
                    person_name = person_name.split(", ")[1] + " " + person_name.split(", ")[0]

                    yield {
                        "type": "club_roles",
                        "club_name": name,
                        "person_name": person_name,
                        "role": role,
                    }

        if response.css("li.pager__item.pager__item--last"):
            last_page_url = response.css(
                "li.pager__item.pager__item--last>a::attr(href)"
            ).extract_first()
            last_page = int(last_page_url.split("=")[1])

            if current_page < last_page:
                next_page = current_page + 1
                next_page_url = response.url.split("?")[0] + "?page=" + str(next_page)
                yield scrapy.Request(
                    url=next_page_url,
                    callback=self.parse_club_page_roles,
                    meta={"page": next_page},
                )



    def parse_person_page(self, response):
        role = response.meta.get("role")
        data_divs = response.css("div.sabor_data_entity>div")

        name_div = data_divs[0]
        personal_div = data_divs[1]
        sabor_data = data_divs[2]

        name = name_div.css("h2::text").extract_first().strip()
        img_url = personal_div.css("img::attr(src)").extract_first()
        club_name = response.meta.get("club_name")

        memberships = []
        friendships = []

        personal_notes = personal_div.css("div.zivotopis>p::text").extract_first().strip()
        mandates = 1

        for sector in sabor_data.css("div.views-element-container"):
            title = sector.css("div.eva-header>h3::text").extract_first()
            if title:
                title = title.strip()
            else:
                continue

            if title == "Početak obnašanja zastupničkog mandata:":
                # start of mandate
                mandate_start_date = (
                    sector.css("div.field-content::text").extract_first().strip()
                )
            if title == "Klub zastupnika:":
                club_names = sector.css("a::text").extract()
                for i in club_names:
                    # TODO: remove this when parlameter support multiple clubs for a person
                    if 'Klub zastupnika nacionalnih manjina' in i:
                        continue
                    else:
                        club_name = i.strip()

            if title == "Pregled saziva:":
                mandates = len(sector.css("a")) + 1
                

            if title == "Dužnosti u saboru:":
                for commitee_selector in sector.css("div.item-list>ul>li"):
                    temp_commitee = {}

                    temp_commitee["role"] = (
                        commitee_selector.css(
                            "span.views-field-field-funkcija>span::text"
                        )
                        .extract_first()
                        .strip().lower()
                    )

                    if temp_commitee["role"].startswith("zamjen"):
                        # skip Zamjenica memberships
                        continue

                    name_genitiv = commitee_selector.css(
                        "span.views-field-field-naziv-u-genitivu>span>a::text"
                    ).extract_first()
                    name_genitiv_1 = commitee_selector.css(
                        "span.views-field-field-naziv-u-genitivu-1>span>a::text"
                    ).extract_first()
                    name_genitiv_2 = commitee_selector.css(
                        "span.views-field-field-naziv-u-genitivu-2>span>a::text"
                    ).extract_first()
                    if not any([name_genitiv, name_genitiv_1, name_genitiv_2]):
                        if "sabor" in temp_commitee["role"]:
                            commitee_name = "Sabor"
                            temp_commitee["role"] = (
                                temp_commitee["role"].split("sabor")[0].strip()
                            )
                        else:
                            raise Exception("No name found")
                    else:
                        commitee_name = (
                            name_genitiv
                            if name_genitiv
                            else name_genitiv_1 if name_genitiv_1 else name_genitiv_2
                        )

                    temp_commitee["name"] = commitee_name.strip()

                    start_date = commitee_selector.css(
                        "span.views-field-field-od>span::text, span.views-field-field-datum-pocetka-1>span::text"
                    ).extract_first()
                    if start_date:
                        temp_commitee["start_date"] = start_date.strip().strip("() od")

                    memberships.append(temp_commitee)

            if title == "Članstvo u međuparlamentarnim skupinama prijateljstva:":
                # end of mandate
                friendships = sector.css("a::text").extract()

        yield {
            "type": "person",
            "name": name,
            "img_url": self.BASE_URL + img_url if img_url else None,
            "club_role": role,
            "club_name": club_name,
            "commitees": memberships,
            "friendships": list(map(str.strip, friendships)),
            "mandates": mandates,
            "zivotopis": personal_notes,
        }


    def close(self, spider):
        self.myPipeline.save_memberships()
