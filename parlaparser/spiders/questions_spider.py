# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class QuestionsSpider(scrapy.Spider):
    name = 'questions'

    custom_settings = {
        'ITEM_PIPELINES': {
            'parlaparser.pipelines.ParlaparserPipeline': 1
        }
    }

    start_urls = [
        'https://edoc.sabor.hr/ZastupnickaPitanja.aspx',
        ]

    def parse(self, response):       
        num_pages = int(response.css("table.OptionsTable td span::text").extract()[2].strip().split(" ")[1])

        # limiter
        start_page = 1
        #num_pages = 5

        for i in range(start_page, start_page + num_pages):
            form_data = self.validate(response)

            # This is how edoc aspx backend works. callback param need to know how much digits has number
            special_aspx = len(str(i-1)) + 12
            callback_param = 'c0:KV|81;["11296","11295","11294","11293","11292","11291","11290","11289","11288","11265"];GB|' + str(special_aspx) + ';8|GOTOPAGE' + str(len(str(i-1))) + '|' + str(i-1) + ';'

            form_data.update({
                'ctl00$ContentPlaceHolder$gvPitanja$PagerBarB$GotoBox': str(i),
                '__CALLBACKID': 'ctl00$ContentPlaceHolder$gvPitanja',
                '__CALLBACKPARAM': callback_param,
                #'ctl00$ContentPlaceHolder$navFilter': '{&quot;selectedItemIndexPath&quot;:&quot;&quot;,&quot;groupsExpanding&quot;:&quot;0;0;0&quot;}',
                #'ctl00$ContentPlaceHolder$rbtnTraziPo': '0',
            })
            yield scrapy.FormRequest(url='https://edoc.sabor.hr/ZastupnickaPitanja.aspx',
                                     formdata=form_data,
                                     meta={'page': str(i), 'calback': callback_param},
                                     callback=self.parse_list,
                                     method='POST')


    def validate(self, response):
        viewstate = response.css("#__VIEWSTATE::attr(value)").extract()[0]
        viewstategen = response.css("#__VIEWSTATEGENERATOR::attr(value)").extract()[0]
        eventvalidation = response.css("#__EVENTVALIDATION::attr(value)").extract()[0]
        return {'__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategen,
            }




    def parse_list(self, response):
        # print("AGENDA")
        items = response.css("#ctl00_ContentPlaceHolder_gvPitanja_DXMainTable>tr")[1:]
        #logging.error(items)
        if len(items) == 0:
            logging.error("FAIL " + response.meta["page"] + " " + response.meta["calback"])
        for i in items:
            row = i.css("td>a::attr(href)").extract()
            url = 'https://edoc.sabor.hr/' + row[4][2:-2]
            #print(url)
            yield scrapy.Request(url=url, callback=self.parse_question)


    def parse_question(self, response):
        author = response.css("#ctl00_ContentPlaceHolder_lblzastupnikValue::text").extract()
        title = ''.join(response.css("#ctl00_ContentPlaceHolder_PitanjeFonogram *::text").extract())

        ref = response.css("#ctl00_ContentPlaceHolder_lblsazivValue::text").extract()
        date = response.css("#ctl00_ContentPlaceHolder_lbldatumPostavljanjaValue::text").extract()
        typ = response.css("#ctl00_ContentPlaceHolder_lblnacinPostavljanjaValue::text").extract()
        recipient = response.css("#ctl00_ContentPlaceHolder_hledokumentiPitanja::text").extract()
        field = response.css("#ctl00_ContentPlaceHolder_lblpodrucjeValue::text").extract()
        signature = response.css("#ctl00_ContentPlaceHolder_lblsignaturaValue::text").extract()

        link = response.css("#ctl00_ContentPlaceHolder_PitanjeFonogram::attr(href)").extract()

        answer = response.css("#ctl00_ContentPlaceHolder_OdgovorFonogram::attr(href)").extract()
        answer_date = response.css("#ctl00_ContentPlaceHolder_lbldatumOdgovoraValue::text").extract()

        if not answer_date:
            if 'sjednici' in response.css("#ctl00_ContentPlaceHolder_lblnacinPostavljanjaValue::text").extract_first():
                answer_date = date
        yield {'author': author,
               'title': title,
               'ref': ref,
               'date': date,
               'typ': typ,
               'recipient': recipient,
               'field': field,
               'signature': signature,
               'link': link,
               'edoc_url': response.url,
               'answer': answer,
               'answer_date': answer_date}

