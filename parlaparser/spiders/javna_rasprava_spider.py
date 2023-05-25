# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime


class PublicQuestionsSpider(scrapy.Spider):
    name = 'javnarasprava'

    custom_settings = {
        'ITEM_PIPELINES': {
            'parlaparser.pipelines.BihParserPipeline': 1
        }
    }

    start_urls = [
        'https://www.javnarasprava.ba/bih/Parlamentarci',
        'https://www.javnarasprava.ba/fbih/Parlamentarci',
        'https://www.javnarasprava.ba/rs/Parlamentarci',
    ]
    base_url = 'https://www.javnarasprava.ba'

    def parse(self, response):
        for representative_url in set(response.css("div.representative a::attr(href)").extract()):
            yield scrapy.Request(url=self.base_url + representative_url + '/DirektnaPitanja', callback=self.parse_representative)
            yield scrapy.Request(url=self.base_url + representative_url + '/PitanjaNaZakone', callback=self.parse_representative_law)

    def parse_representative(self, response):
        name = response.css(".panel-body dd h2::text").extract_first()

        for div in response.css(".panel-default div.panel-body>div"):
            question = div.css('.question')
            answer = div.css('.answer')

            if question:
                text = question.css('p::text').extract()[1].strip()
                date = question.css("small::text").extract_first().split(':')[1].strip()
                gov_id = question.css("span::attr(id)")[0].extract().split('_')[1]

                yield {
                    'text': text,
                    'person_name': name,
                    'date': date,
                    'gov_id': gov_id,
                    'type': 'question'
                }

            if answer:
                text = ' '.join(map(str.strip, answer.css('p::text').extract()))
                date = answer.css("small::text").extract_first().split(':')[1].strip()
                question_gov_id = gov_id
                gov_id = answer.css("span::attr(id)")[0].extract().split('_')[1]
                yield {
                    'text': text,
                    'date': date,
                    'gov_id': gov_id,
                    'question_gov_id': question_gov_id,
                    'type': 'answer'
                }

    def parse_representative_law(self, response):
        name = response.css(".panel-body dd h2::text").extract_first()

        for div in response.css(".panel-default div.panel-body>div"):
            question = div.css('.question')
            answer = div.css('.answer')

            if question:
                text = question.css('p::text').extract()[1].strip()
                date = question.css("small::text").extract_first().split(':')[1].strip()
                gov_id = question.css("span::attr(id)")[0].extract().split('_')[1]
                law = div.css("h4>a::text").extract_first()

                text = f'Pitanje postavljeno na {law}: {text}'

                yield {
                    'text': text,
                    'person_name': name,
                    'date': date,
                    'gov_id': gov_id,
                    'type': 'question'
                }

            if answer:
                text = ' '.join(map(str.strip, answer.css('p::text').extract()))
                date = answer.css("small::text").extract_first().split(':')[1].strip()
                question_gov_id = gov_id
                gov_id = answer.css("span::attr(id)")[0].extract().split('_')[1]
                yield {
                    'text': text,
                    'date': date,
                    'gov_id': gov_id,
                    'question_gov_id': question_gov_id,
                    'type': 'answer'
                }
