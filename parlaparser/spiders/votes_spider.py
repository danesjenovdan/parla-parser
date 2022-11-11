import scrapy
from datetime import datetime
import json, requests

class VotesSpider(scrapy.Spider):
    name = 'votes'
    custom_settings = {'ITEM_PIPELINES': {'parlaparser.pipelines.ParlaparserPipeline': 1}}
    BASE_URL = 'https://www.sabor.hr'
    start_urls = [
     'https://www.sabor.hr/hr/sjednice/pregled-dnevnih-redova']
    THIS_SAZIV_ID = 170
    skip_urls = [
     'https://www.sabor.hr/prijedlog-polugodisnjeg-izvjestaja-o-izvrsenju0004',
     'https://www.sabor.hr/prijedlog-odluke-o-izboru-tri-suca-ustavnog-suda-r']

    def parse(self, response):
        data = {'view_name':'sabor_data',
         'view_display_id':'dnevni_redovi',
         'field_saziv_target_id':'117054'}
        print(data)
        url = 'https://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax'
        for select in response.css('[name="plenarna_id"] option')[1:2]:
            value = select.css('::attr(value)').extract_first()
            if value:
                print(100 * '-')
                print(select.css('::text').extract_first(), value)
                print(100 * '-')
                data['plenarna_id'] = str(value)
                yield scrapy.FormRequest(url, callback=(self.parser_session), method='POST', formdata=data)

    def parser_session(self, response):
        j_data = json.loads(response.css('textarea::text').extract_first())
        my_response = scrapy.selector.Selector(text=(j_data[4]['data'].strip()))
        session_name = my_response.css('.group h2::text').extract_first()
        for line in my_response.css('.content li'):
            status = line.css('.dnevni-red-stavka::attr(data-status)').extract_first()
            url = line.css('a::attr(href)').extract_first()
            if not url:
                return
            yield scrapy.Request(
                url=(self.BASE_URL + url),
                callback=(self.parser_motion),
                meta={'parent':response.url,
                'session_name':session_name,
                'status':status})

    def parser_motion(self, response):
        item_type = None
        if response.meta['status'] == '8':
            item_type = 'vote'
        else:
            item_type = 'legislation'
        link_in_result = response.css('.views-field-field-status-tekstualni .field-content a::attr(href)').extract()
        child_motion_urls = response.css('.popis-sadrzaja .item-list li a::attr(href)').extract()
        for child_motion_url in child_motion_urls:
            yield scrapy.Request(url=(self.BASE_URL + child_motion_url), callback=(self.parser_motion), meta=(response.meta))

        if child_motion_urls:
            return
        title = response.css('.views-row h1::text').extract_first()
        result_and_data = ''.join(response.css('.field-content p ::text').extract()).split('\n')
        vote_date = response.css('.views-field-field-vrijeme-izglasavanja .field-content::text').extract_first()
        tid = response.url.split('tid=')[1]
        date_to_procedure = response.css('.views-field-field-datum-ulaska-u-proceduru time::attr(datetime)').extract_first()
        ballots_link = []
        motion_data = None
        docs = []
        raw_docs = response.css('.view-display-id-vezane_informacije .field-content')
        for doc in raw_docs:
            if doc.css('a::attr(href)').extract()[0].startswith("http"):
                url = doc.css('a::attr(href)').extract()[0]
            else:
                url = 'https://www.sabor.hr' + doc.css('a::attr(href)').extract()[0]
            docs.append({'url': url,  'text':doc.css('a::text').extract()[0]})


        raw_docs = response.css('.view-display-id-amandmani .paragraph--type--accordions')
        for doc in raw_docs:
            docs.append({'url':doc.css('a::attr(href)').extract()[0],  'text':doc.css('a::text').extract()[0]})

        data = {
            'title':title,
            'results_data':result_and_data,
            'type':item_type,
            'date':vote_date,
            'url':response.url,
            'docs':docs,
            'parent':response.meta['parent'],
            'session_name':response.meta['session_name'],
            'date_to_procedure':date_to_procedure
        }
        if link_in_result:
            vote_ajax_data = []
            ids = '-'.join([link.split('ID=')[1] for link in link_in_result])
            motions_data = requests.get(('https://www.sabor.hr/hr/rezultati-glasovanja-parse-itv/%s/' % ids), verify=False).json()
            for motion_data in motions_data:
                yield self.parse_ballots(motion_data, response.url, motion_data['id'], docs, response.meta['session_name'])

            return
        motion_data = requests.get(('https://sabor.hr/hr/rezultati-glasovanja-servis/%s/' % tid), verify=False).json()
        if motion_data['title']:
            yield self.parse_ballots(motion_data, response.url, tid, docs, response.meta['session_name'])
            return
        data.update(id=tid)
        yield data

    def parse_ballots(self, response_data, url, id, docs, session_name):
        ballots_response = scrapy.selector.Selector(text=(response_data['votes']))
        ballots = []
        for i in ballots_response.css('.votes .vote-row'):
            name = i.css('.name::text').extract_first()
            if not name:
                name = i.css('.name a::text').extract_first().replace(',', '')
            option = i.css('.vote > span::attr(class)').extract_first()
            ballots.append({'voter':name,  'option':option})

        title = response_data['title']
        if title[1] == ')':
            title = title[2:].strip()
        out_data = {
            'title':title,
            'time':response_data['time'],
            'for_count':response_data['for_count'],
            'against_count':response_data['against_count'],
            'abstained_count':response_data['abstained_count'],
            'ballots':ballots,
            'url':url,
            'id':id,
            'type':'vote_ballots',
            'docs':docs,
            'session_name':session_name
        }
        return out_data
