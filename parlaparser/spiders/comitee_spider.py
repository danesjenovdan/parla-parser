import scrapy
from datetime import datetime
import json, requests

class ComiteeSpider(scrapy.Spider):
    name = 'comitee'
    ajax_url = 'https://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax'
    calendar_link = 'https://sabor.hr/hr/radna-tijela/najave/dan/%s/odbor/%s'
    custom_settings = {'ITEM_PIPELINES': {'parlaparser.pipelines.ParlaparserPipeline': 1}}
    BASE_URL = 'http://www.sabor.hr'
    start_urls = [
     'https://sabor.hr/hr/radna-tijela/odbori-i-povjerenstva']
    THIS_SAZIV_ID = 117054
    roles = {'Predsjednik':'president',
     'Predsjednica':'president',
     'Potpredsjednik':'deputy',
     'Potpredsjednica':'deputy',
     'Potpredsjednici':'deputy',
     'Članovi':'member'}

    def __init__(self, parse_memberships=False, parse_calendar=True, **kwargs):

        # TODO enable parsing calendar

        self.start_urls = [
         'https://sabor.hr/hr/radna-tijela/odbori-i-povjerenstva']
        self.parse_calendar = parse_calendar
        self.parse_memberships = parse_memberships
        (super().__init__)(**kwargs)

    def parse(self, response):
        for i in response.css('.item-list li'):
            a = i.css('a')
            link = a.css('::attr(href)').extract_first()
            wb_name = a.css('::text').extract_first()
            if 'https://sabor.hr' in link:
                wb_link = link
            else:
                wb_link = 'https://sabor.hr' + link.strip()
            yield scrapy.Request(
                url=wb_link,
                meta={'wb_name': wb_name},
                callback=(self.parse_single_wb),
                priority=6)

    def parse_single_wb(self, response):
        if self.parse_memberships:
            print('Membership')
            for i in response.css('#tab-o-odboru > div')[1].css('.view-group'):
                role = self.roles[i.css('h4::text').extract_first().strip()]
                for member in i.css('.views-row a::text').extract():
                    yield {
                        'role':role,
                        'name':member,
                        'wb_title':response.meta['wb_name'],
                        'type':'wb_membership'
                    }

        else:
            wb_id = response.css('.calendar::attr(data-odbor-id)').extract_first()
            drupal_settings = json.loads(response.css('script[data-drupal-selector="drupal-settings-json"]::text').extract_first())
            for datum in drupal_settings['datumi']:
                if self.parse_calendar:
                    yield scrapy.Request(url=self.calendar_link % (datum, wb_id),
                        callback=self.parse_wb_sessions_from_callendar,
                        meta={
                            'wb_name':response.meta['wb_name'],
                            'wb_id':wb_id
                        },
                        priority=5
                    )

            data = {
                'view_name':'sabor_eva',
                'field_saziv_target_id': str(self.THIS_SAZIV_ID),
                'odbor_id': str(wb_id),
                'view_display_id':'sjednice_odbora_po_sazivu',
                'ajax_page_state[libraries]':'better_exposed_filters/general,calendar/calendar.theme,core/drupal.states,core/html5shiv,isiteopen/awesome5,isiteopen/bootstrap,isiteopen/global,isiteopen/isiteopen.accordions,isiteopen/isiteopen.gallery-image-grid,isiteopen/js-xsls,isiteopen/pdfmake,perpetuum_font_resize/perpetuum_font_resize,perpetuum_odbor_kalendar/perpetuum_odbor_kalendar,sabor_helper/sabor-helper,sabor_services/flowplayer,sabor_services/flowplayerhls,sabor_services/moment,sabor_services/sabor-services,system/base,views/views.ajax,views/views.module'}
            yield scrapy.FormRequest(
                self.ajax_url,
                callback=self.parse_wb_ajax_reponse,
                method='POST',
                formdata=data,
                meta={
                    'wb_name':response.meta['wb_name'],
                    'wb_id':wb_id
                },
                priority=3)

    def parse_wb_ajax_reponse(self, response):
        j_data = json.loads(response.css('textarea::text').extract_first())
        my_response = scrapy.selector.Selector(text=(j_data[(len(j_data) - 1)]['data'].strip()))
        for session in my_response.css('.item-list'):
            session_name = session.css('h3::text').extract_first()
            for doc in session.css('li a'):
                link = doc.css('::attr(href)').extract_first()
                if not link:
                    pass
                else:
                    if 'https://sabor.hr' in link:
                        vote_url = link
                    else:
                        vote_url = 'https://sabor.hr' + link.strip()
                    yield scrapy.Request(
                        url=vote_url,
                        meta={'session_name':session_name.split('-')[0].strip(), 
                        'date':session_name.split('-')[1].strip(), 
                        'wb_name':response.meta['wb_name']},
                        callback=(self.parse_wb_vote),
                        priority=2)

    def parse_wb_vote(self, response):
        item_title = response.css('.field-content::text').extract_first()
        try:
            item_text = response.css('.sabor_data_entity div p::text').extract()
        except:
            item_text = None
        else:
            wb_title = response.css('.pre-title-first::text').extract_first()
            datetime_utc = response.css('.sabor_data_entity time::attr(datetime)').extract_first()
            yield {
                'type':'session_vote_texts',
                'item_title':item_title,
                'item_text':item_text,
                'session_name':response.meta['session_name'],
                'wb_title':response.meta['wb_name'],
                'url':response.url,
                'datetime_utc':datetime_utc,
                'date':response.meta['date']
            }

    def parse_wb_sessions_from_callendar(self, response):
        for session in response.css('.item.row'):
            name = session.css('a::text').extract_first()
            link = session.css('a::attr(href)').extract_first()
            if 'https://sabor.hr' in link:
                calendar_url = link
            else:
                calendar_url = 'https://sabor.hr' + link.strip()
            yield scrapy.Request(
                url=calendar_url,
                callback=(self.parse_single_session_from_calendar),
                meta={
                    'wb_name': response.meta['wb_name']
                },
                priority=4
            )

    def parse_single_session_from_calendar(self, response):
        datetime_utc = response.css('.najava-datumi time::attr(datetime)').extract_first()
        session_name = response.css('#block-isiteopen-page-title--2 span::text').extract_first()
        try:
            agenda_items = response.css('article div p::text').extract()
        except:
            agenda_items = []
        else:
            yield {
                'type':'calendar_session',
                'datetime_utc':datetime_utc,
                'session_name':session_name,
                'agenda_items':agenda_items,
                'wb_title':response.meta['wb_name']
            }
