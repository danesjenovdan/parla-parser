# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class SessionSpider(scrapy.Spider):
    name = 'sessions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'https://parlament.ba/session/Read?ConvernerId=1',
        'https://parlament.ba/session/Read?ConvernerId=2',
        ]
    base_url = 'http://parlament.ba'

    def __init__(self, house=None, gov_id=None, parse_type=None, *args,**kwargs):
        super(SessionSpider, self).__init__(*args, **kwargs)
        self.house = house
        self.gov_id = gov_id
        self.parse_type = parse_type

    def parse(self, response):
        session_of = response.css(".article header h1::text").extract_first()

        if self.house:
            if self.house == 'lords' and session_of == 'Dom naroda':
                return
            elif self.house == 'people' and session_of == 'Predstavnički dom':
                return

        for link in response.css('.list-articles li a::attr(href)').extract():
            print('parse link')
            yield scrapy.Request(url=self.base_url + link, callback=self.session_parser, meta={'session_of': session_of})

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def session_parser(self, response):
        session_gov_id = response.url.split('id=')[1].split('&')[0]

        if self.gov_id:
            if self.gov_id != session_gov_id:
                return

        session_name = response.css('.article header h1::text').extract_first()
        start_date = ''.join([i.strip() for i in response.css('.schedule::text').extract()])
        start_time = response.css('.time::text').extract_first()

        agenda_items = response.css(".session-schedule p::text").extract()

        print(session_name)

        data = {
            'session_of': response.meta['session_of'],
            'gov_id': session_gov_id,
            'name': session_name,
            'start_date': start_date,
            'start_time': start_time,
            'agenda_items': agenda_items
        }

        for li in response.css('.session-box .list-unstyled li a'):
            key = li.css('a::text').extract_first()
            link = li.css('a::attr(href)').extract_first()
            print('link', link)
            if key == 'Rezultati glasanja' and link and (self.parse_type in ['votes', None]):
                # parse votes
                file_name = str(session_gov_id) + '-votes.pdf'
                data['votes'] = {
                    'file_name': file_name,
                    'url': self.base_url + link
                }

            elif key == 'Stenogram' and link and (self.parse_type in ['speeches', None]):
                # parse speeches
                file_name = str(session_gov_id) + '-speeches.pdf'
                data['speeches'] = {
                    'file_name': file_name,
                    'url': self.base_url + link
                }
            elif key == 'Izvještaj' and link and (self.parse_type in ['legislation', None]):
                file_name = str(session_gov_id) + '-izvjestaj.pdf'
                data['izvjestaj'] = {
                    'file_name': file_name,
                    'url': self.base_url + link
                }

        yield data

    def save_pdf(self, response):
        file_name = response.meta['name']
        self.logger.info('Saving PDF %s', file_name)
        with open('files/'+file_name, 'wb') as f:
            f.write(response.body)
