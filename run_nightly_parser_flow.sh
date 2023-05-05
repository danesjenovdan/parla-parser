#!/bin/bash
cd /app
echo "lematize speeches"
python manage.py lemmatize_speeches
echo "set tfidf"
python manage.py set_tfidf_for_sessions
echo "run analysis for today"
python manage.py daily_update
echo "update legislation to solr"
python manage.py upload_legislation_to_solr
echo "update speeches to solr"
python manage.py upload_speeches_to_solr
echo "update votes to solr"
python manage.py upload_votes_to_solr
echo "update agenda-items to solr"
python manage.py upload_agenda_items_to_solr
echo "send notifications"
python manage.py send_daily_notifications
