import os
import requests
import operator
import re
import nltk
from rq import Queue
from rq.job import Job
from worker import conn
from flask import Flask, render_template, request, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from stop_words import stops
from collections import Counter
from bs4 import BeautifulSoup


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

q = Queue(connection=conn)

from models import *

print('blah', os.environ['APP_SETTINGS'])
print('conn is: ', conn)

def count_and_save_words(url):
    # you'll see this in the redis window
    print('COUNT AND SAVE WORDS CALLED')
    errors = []

    # gets the url
    try:
        r = requests.get(url)
    except:
        errors.append(
            "Unable to get URL. Please make sure it's valid and try again."
        )
        return {"error": errors}


    # text processing
    raw = BeautifulSoup(r.text, 'html.parser').get_text()
    nltk.data.path.append('./nltk_data/')  # set the path
    tokens = nltk.word_tokenize(raw)
    text = nltk.Text(tokens)

    # remove punctuation, count raw words
    nonPunct = re.compile('.*[A-Za-z].*')
    raw_words = [w for w in text if nonPunct.match(w)]
    raw_word_count = Counter(raw_words)



    # stop words
    no_stop_words = [w for w in raw_words if w.lower() not in stops]
    no_stop_words_count = Counter(no_stop_words)

    # here's where i think it's messing up
    # save the results

    # it makes it this far
    # print('eskimo potpie........!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!111', url, 
    #     raw_word_count, no_stop_words)



    # print('database session', db.session)



    try:
        # it doesn't seem to make it this far?
        # print(sys.version)
        # print('\n COMMIT TO DATABASE \n')
        print('URL is ', url)
        print('raw_word_count is ', raw_word_count)
        print('result_no_stop_words ', no_stop_words_count)


        result = Result(
            url="http://127.0.0.1:5000/",
            result_all={'Wordcount': 2, '1000px': 1, 'max-width': 1, '.container': 1, 'Submit': 1},
            result_no_stop_words={'Wordcount': 2, '1000px': 1, 'max-width': 1, '.container': 1, 'Submit': 1}
        )

        print("PRINT STATMENT NOT BEING REACHED?")
        print("WHY ARE YOU NOT PRINTING THIS THEN?!!!!? ", result.url, result.result_all, 
            result.result_no_stop_words.values())

        db.session.add(result)
        db.session.commit()
        print("RESULT ID IS: ", result.id)
        return result.id
    except:
        errors.append("Unable to add item to database.")
        return {"error": errors}


@app.route('/', methods=['GET', 'POST'])
def index():
    results = {}
    if request.method == "POST":
        # get url that the person has entered
        url = request.form['url']
        if 'http://' not in url[:7]:
            url = 'http://' + url
        job = q.enqueue_call(
            func=count_and_save_words, args=(url,), result_ttl=5000
        )
        print(job.get_id())

    return render_template('index.html', results=results)


@app.route("/results/<job_key>", methods=['GET'])
def get_results(job_key):

    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        result = Result.query.filter_by(id=job.result).first()
        results = sorted(
            result.result_no_stop_words.items(),
            key=operator.itemgetter(1),
            reverse=True
        )[:10]
        return jsonify(results)
    else:
        return "Nay!", 202


if __name__ == '__main__':
    app.run()