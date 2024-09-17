import scrapy
from datetime import datetime
import json, requests, re

class VotesSpider(scrapy.Spider):
    name = 'votes'
    custom_settings = {'ITEM_PIPELINES': {'parlaparser.pipelines.ParlaparserPipeline': 1}}
    BASE_URL = 'https://www.sabor.hr'
    start_urls = [
     'https://www.sabor.hr/hr/sjednice/pregled-dnevnih-redova']

    skip_urls = [
     'https://www.sabor.hr/prijedlog-polugodisnjeg-izvjestaja-o-izvrsenju0004',
     'https://www.sabor.hr/prijedlog-odluke-o-izboru-tri-suca-ustavnog-suda-r']

    def parse(self, response):
        data = {
            'view_name':'sabor_data',
            'view_display_id':'dnevni_redovi',
            'field_saziv_target_id':'144982'
        }
        print(data)
        post_url = 'https://www.sabor.hr/hr/views/ajax?_wrapper_format=drupal_ajax'
        for select in response.css('[name="field_plenarna_sjednica_target_id"] option')[1:3]:
            value = select.css('::attr(value)').extract_first()
            if value:
                print(100 * '-')
                print(select.css('::text').extract_first(), value)
                print(100 * '-')
                data['field_plenarna_sjednica_target_id'] = str(value)
                #yield scrapy.FormRequest(post_url, callback=(self.parser_session), method='POST', formdata=data)
                get_url = f"{self.BASE_URL}/hr/sjednice/pregled-dnevnih-redova?field_saziv_target_id={data['field_saziv_target_id']}&field_plenarna_sjednica_target_id={value}"
                yield scrapy.Request(
                    url=get_url,
                    callback=(self.parser_session),
                )

    def parser_session(self, response):
        if response.request.method == 'POST':
            j_data = json.loads(response.css('textarea::text').extract_first())
            my_response = scrapy.selector.Selector(text=(j_data[4]['data'].strip()))
        else:
            my_response = response
        session_name = my_response.css('.group h2::text').extract_first()
        end_date_text = None
        start_date_text = None

        find_end_row = r"Sjednica je zaključena \d{1,2}\. \w{5,8} \d{4}."
        find_start_row = r"Sjednica će započeti u \w*, \d{1,2}\. \w{5,8} \d{4}."
        date_regex = r"\d{1,2}\. \w{5,8} \d{4}"
        session_intros = my_response.css('.intro p::text').extract()
        for session_intro in session_intros:
            session_intro = session_intro.replace('\xa0', ' ')
            end_text = re.search(find_end_row, session_intro)
            start_text = re.search(find_start_row, session_intro)
            print(end_text, start_text)
            if end_text:
                end_text = end_text.group()
                date_text = re.search(date_regex, session_intro)
                date_text = date_text.group()
                if date_text:
                    end_date_text = date_text
            if start_text:
                date_text = re.search(date_regex, session_intro)
                date_text = date_text.group()
                if date_text:
                    start_date_text = date_text

        for line in my_response.css('.content li'):
            status = line.css('.dnevni-red-stavka::attr(data-status)').extract_first()
            url = line.css('a::attr(href)').extract_first()
            if not url:
                return
            yield scrapy.Request(
                url=(self.BASE_URL + url),
                callback=(self.parser_motion),
                meta={
                    'parent':response.url,
                    'session_name':session_name,
                    'status':status,
                    'end_date': end_date_text,
                    'start_date': start_date_text
                    })
            
    def get_time(self, response, class_name):
        field_content = response.css(f'{class_name} > .field-content')
        if field_content.css("time"):
            return field_content.css("time::attr(datetime)").extract_first().split('+')[0]
        else:
            return field_content.css('::text').extract_first()


    def parser_motion(self, response):
        item_type = None
        if response.meta['status'] == '8':
            item_type = 'vote'
        else:
            item_type = 'legislation'
        link_in_result = response.css('div.views-field > span.field-content > a.akt-rezultati-service')
        child_motion_urls = response.css('.item-list li a::attr(href)').extract()
        for child_motion_url in child_motion_urls:
            yield scrapy.Request(url=(self.BASE_URL + child_motion_url), callback=(self.parser_motion), meta=(response.meta))

        if child_motion_urls:
            return
        title = response.css('div.field-content::text').extract_first()
        result_and_data = ''.join(response.css('.field-content p ::text').extract()).split('\n')
        vote_date = self.get_time(response, ".views-field-field-vrijeme-izglasavanja")
        tid = response.url.split('tid=')[1]
        date_to_procedure = self.get_time(response, ".views-field-field-datum-ulaska-u-proceduru")
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
            'session_start_date':response.meta['start_date'],
            'session_end_date':response.meta['end_date'],
            'date_to_procedure':date_to_procedure
        }

        motion_data = requests.get(f"https://www.sabor.hr/hr/rezultati-glasovanja-servis/{tid}/", verify=False)
        if motion_data.status_code == 200:
            motion_data = motion_data.json()
            yield self.parse_ballots(motion_data, response.url, tid, docs, response.meta['session_name'], response.meta['start_date'], response.meta['end_date'],)
            return
        data.update(id=tid)
        yield data

    def parse_ballots(self, response_data, url, id, docs, session_name, session_start_date, session_end_date):
        ballots_response = scrapy.selector.Selector(text=(response_data.get('votes', '')))
        ballots = []
        for i in ballots_response.css('.votes .vote-row'):
            name = i.css('.name::text').extract_first()
            if not name:
                name = i.css('.name a::text').extract_first()
                name = " ".join(reversed(name.split(", ")))
            option = i.css('.vote > span::attr(class)').extract_first()
            ballots.append({'voter':name,  'option':option})

        title = response_data.get('title', '')
        if not title:
            title = response_data['naziv']
        if title[1] == ')':
            title = title[2:].strip()
        out_data = {
            'title':title,
            'time':response_data.get('time', ''),
            'for_count':response_data.get('for_count'),
            'against_count':response_data.get('against_count'),
            'abstained_count':response_data.get('abstained_count'),
            'ballots':ballots,
            'url':url,
            'id':id,
            'type': 'vote_ballots' if ballots else 'vote',
            'docs':docs,
            'session_name':session_name,
            'session_start_date':session_start_date,
            'session_end_date':session_end_date
        }
        return out_data
