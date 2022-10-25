FROM rg.fr-par.scw.cloud/djnd/parladata-hrvaska:latest

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get -y install locales locales-all

RUN apt-get install libpoppler-cpp-dev -y

RUN /usr/local/bin/python -m pip install --upgrade pip

RUN mkdir /parser
WORKDIR /parser

COPY requirements.txt /parser/
RUN pip install -r requirements.txt

COPY . /parser

CMD bash run_nightly_parser_flow.sh
