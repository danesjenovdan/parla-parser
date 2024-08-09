import logging
logger = logging.getLogger('base logger')

class BaseParser(object):
    def __init__(self, reference):
        self.reference = reference

    def parse_edoc_person(self, data):
        splited = data.split('(')
        name = splited[0]
        if len(splited) > 1:
            pg = splited[1].split(')')[0]
        else:
            splited = data.split('/')
            if len(splited) > 1:
                name = splited[0]
                pg = splited[1].strip()
                if ';' in pg:
                    pg = pg.replace(';', '')
                if 'Vlade' in pg:
                    pg = 'gov'
            else:
                pg = None
        name = ' '.join(reversed(list(map(str.strip, name.split(',')))))
        return (name, pg)

    def remove_leading_zeros(self, word, separeted_by=[',', '-', '/']):
        for separator in separeted_by:
            word = separator.join(map(lambda x: x.lstrip('0'), word.split(separator)))
        return word
