# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class ActSpider(scrapy.Spider):
    name = 'acts'
    custom_settings = {
        'ITEM_PIPELINES': {
            'bihparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'http://parlament.ba/oLaw/GetOLawsBySubmissionDate?SearchTerm=&MandateId=6&DateFrom=&DateTo=',
        ]

    map_of_keys = {
        'Broj i datum Prijedloga zakona u PDPSBiH': 'epa',
        'Status u DNPSBiH': 'status',
        'Nadležna komisija': 'mdt',
        'Status i faza postupka': 'faza',
        'Broj i datum Prijedloga zakona': 'epa',
        'Konačni status u PSBiH': 'status',
        'Red. br. i datum sjednice - tačka dnevnog reda': 'date',
        'Utvrđen na sjednici predlagača': 'session',
    }
    base_url = 'http://parlament.ba'

    def parse(self, response):
        for link in response.css('.list-articles li a::attr(href)').extract():
            yield scrapy.Request(url=self.base_url + link, callback=self.legislation_parser)

        next_page = response.css('.PagedList-skipToNext a::attr(href)').extract_first()
        if next_page:
            yield scrapy.Request(url=self.base_url + next_page, callback=self.parse)

    def legislation_parser(self, response):
        title = response.css(".article header h1::text").extract_first()
        uid = response.url.split('lawId=')[1].split('&')[0]
        data = {
            'text': title,
            'uid': uid,
            'url': response.url
        }
        for line in response.css('.table-minus .table-docs tr'):
            #print(line.css('th').extract_first())
            line_key = line.css('th::text').extract_first()
            if line_key:
                for key in self.map_of_keys.keys():
                    if key in line_key:
                        data[self.map_of_keys[key]] = line.css('td::text').extract_first()

        yield data
