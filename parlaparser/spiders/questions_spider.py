# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime


class QuestionsSpider(scrapy.Spider):
    name = 'questions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'parlaparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'https://parlament.ba/oQuestion/GetORQuestions?RDId=&Rep-7=&Rep-6=&Rep-4=&MandateId=7&DateFrom=&DateTo=',
        'https://parlament.ba/oQuestion/GetODQuestions?RDId=&Del-7=&Del-6=&Del-4=&MandateId=7&DateFrom=&DateTo=',
    ]
    base_url = 'http://parlament.ba'

    data_map = {
        'Poslanik': 'name',
        'Delegat': 'name',
        'Broj i datum dokumenta': 'date_fake',
        'Pitanje postavljeno u pisanoj formi - subjekt i datum': 'asigned',
        'Nadležni subjekt kome je pitanje postavljeno u usmenoj formi': 'asigned',
        'Sjednica na kojoj je pitanje usmeno postavljeno nadležnom subjektu': 'session',
        'Tekst pitanja (identičan usvojenom zapisniku)': 'text',
        'Saziv': 'mandate'
    }

    def parse(self, response):
        questions_of = response.css(".article header h1::text").extract_first()
        for row in response.css('.list-articles li a'):
            link = row.css('::attr(href)').extract_first()
            date = row.css('p.date::text').extract_first().strip()
            yield scrapy.Request(url=self.base_url + link, callback=self.question_parser, meta={'date': date})

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        print("!!---->>>>  ", next_page)
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def question_parser(self, response):
        table = response.css('.table-minus .table-docs')[0]
        date = response.meta['date']
        json_data = {'ref': response.url.split('contentId=')[1].split('&')[0],
                     'links': [],
                     'url': response.url,
                     'text': '',
                     'asigned': None,
                     'date': date}
        try:
            links = response.css('.table-minus .table-docs')[1]
            for line in links.css('tr'):
                head = line.css('th::text').extract_first()
                data = line.css('td a::attr(href)').extract_first()
                json_data['links'].append({'name': head, 'url': data})
        except:
            pass
        for line in table.css('tr'):
            head = line.css('th::text').extract_first()
            data = line.css('td::text').extract_first()
            try:
                json_data[self.data_map[head]] = data
            except:
                print('***\n***\n*** Define KEY:', head)
                print('\n***\n***')
        yield json_data
