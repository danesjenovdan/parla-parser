# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime

class ClubSpider(scrapy.Spider):
    name = 'clubs'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
            #'bihparser.pipelines.BihImagesPipeline': 2
        }
    }

    start_urls = [
        'http://parlament.ba/Content/Read/64?title=KluboviposlanikauPredstavni%C4%8Dkomdomu',
        ]

    def parse(self, response):
        
        for i, mp in enumerate(response.css('.list-contacts li')):
            name, members = mp.css('p')
            name = name.css('strong::text').extract_first()
            members = members.css('::text').extract_first()
            #print(name, members)
            print('\n', name.strip())
            for member in members.split(','):
                role = 'member'
                if '(' in member:
                    splited = member.split('(')
                    member = splited[0]
                    role = self.parse_role(splited[1])

                if '  ' in member:
                    member = member.replace('  ', ' ')

                print(member.strip(), role)

                yield {'club_name': name.strip(),
                       'role': role,
                       'member': member.strip()}



    def parse_role(self, name):
        if 'zamjenica' in name or 'zamjenik' in name:
            return 'deputy'
        elif 'predsjedavajući' in name or 'predsjedavajuća' in name:
            return 'president'
        else:
            return 'member'

