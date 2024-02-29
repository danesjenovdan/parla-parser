# -*- coding: utf-8 -*-
import scrapy
import logging

from datetime import datetime

class SpeechSpider(scrapy.Spider):
    name = 'speeches'

    custom_settings = {
        'ITEM_PIPELINES': {
            'parlaparser.pipelines.ParlaparserPipeline': 1
        }
    }

    start_urls = [
        'https://edoc.sabor.hr/Fonogrami.aspx',
        ]

    def parse(self, response):
        num_pages = int(response.css("table.OptionsTable td span::text").extract()[2].strip().split(" ")[1])

        # optimization limiter
        start_page = 1
        num_pages = 5

        for i in range(start_page, start_page + num_pages):
            form_data = self.validate(response)

            # This is how edoc aspx backend works. callback param need to know how much digits has number
            special_aspx = len(str(i-1)) + 12
            callback_param = 'c0:KV|2;[];GB|' + str(special_aspx) + ';8|GOTOPAGE' + str(len(str(i-1))) + '|' + str(i-1) + ';'

            form_data.update({
                'ctl00$ContentPlaceHolder$gvFonogrami$PagerBarB$GotoBox': str(i),
                '__CALLBACKID': 'ctl00$ContentPlaceHolder$gvFonogrami',
                '__CALLBACKPARAM': callback_param,
                #'ctl00$ContentPlaceHolder$navFilter': '{&quot;selectedItemIndexPath&quot;:&quot;&quot;,&quot;groupsExpanding&quot;:&quot;0;0;0&quot;}',
                #'ctl00$ContentPlaceHolder$rbtnTraziPo': '0',
            })
            yield scrapy.FormRequest(url='https://edoc.sabor.hr/Fonogrami.aspx',
                                     formdata=form_data,
                                     meta={'page': str(i), 'calback': callback_param},
                                     callback=self.parse_agenda,
                                     method='POST')


    def validate(self, response):
        viewstate = response.css("#__VIEWSTATE::attr(value)").extract()[0]
        viewstategen = response.css("#__VIEWSTATEGENERATOR::attr(value)").extract()[0]
        eventvalidation = response.css("#__EVENTVALIDATION::attr(value)").extract()[0]
        return {'__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategen,
            }


    def parse_agenda(self, response):
        # print("AGENDA")
        items = response.css("#ctl00_ContentPlaceHolder_gvFonogrami_DXMainTable>tr")[1:]
        #logging.error(items)
        if items == 0:
            logging.error("FAIL " + response.meta["page"] + " " + response.meta["calback"])
        else:
            logging.error("OK " + response.meta["page"] + " " + response.meta["calback"])
        for i in items:
            row = i.css("td>a::attr(href)").extract()
            url = 'https://edoc.sabor.hr' + row[4][2:-2]
            #print(url)
            yield scrapy.Request(url=url, callback=self.parse_speeches)


    def parse_speeches(self, response):
        session_ref = response.css("#ctl00_ContentPlaceHolder_lblSazivSjednicaDatum::text").extract()
        date_of_session = response.css(".dateString::text").extract()[0].strip()
        agendas = response.css("#ctl00_ContentPlaceHolder_rptMain_ctl00_divTileShape0")
        agendas_nums = list(map(str.strip, agendas.css("#ctl00_ContentPlaceHolder_rptMain_ctl00_lblTdrBrojevi::text").extract_first().split(';')))
        agenda_texts = list(map(str.strip, agendas.css(".contentList li::text").extract()))
        agendas_dict = [{'order':i, 'text': j} for i, j in list(zip(agendas_nums, agenda_texts))]
        speech_date = date_of_session
        order = 0
        speeches = []
        try:
            agenda_id = response.url.split('=')[1]
        except:
            agenda_id = 0
        for line in response.css("#ctl00_Updatepanel > div"):
            # update speech date
            if line.css('.tileShape'):
                speech_date = line.css(".dateString::text").extract_first().strip()
                continue
            elif line.css('.singleContentContainer'):
                if line.css('.specialContentContainer'):
                    continue
                content = '\n'.join(map(str.strip, line.css(".singleContent dd::text").extract()))
                speaker = line.css(".speaker h2::text").extract_first()
                order += 1
                speeches.append({
                    'order': order,
                    'speaker': speaker,
                    'content': content,

                   })
        yield {
            'date': speech_date,
            'session_ref': session_ref,
            'agenda_id': agenda_id,
            'agendas': agendas_dict,
            'speeches': speeches
        }
