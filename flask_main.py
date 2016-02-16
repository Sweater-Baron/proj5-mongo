"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import render_template
from flask import request
from flask import url_for
from flask import redirect

import json
import logging
import operator
import re

# Date handling 
import arrow # Replacement for datetime, based on moment.js
from dateutil import tz  # For interpreting local times

# Mongo database
from pymongo import MongoClient
from bson.objectid import ObjectId


###
# Globals
###
import CONFIG

app = flask.Flask(__name__)

try: 
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.memos
    collection = db.dated

except:
    print("Failure opening database. Is Mongo running? Correct password?")
    sys.exit(1)

import uuid
app.secret_key = str(uuid.uuid4())

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  flask.session['memos'] = get_memos()
#  for memo in flask.session['memos']:
#      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')


@app.route("/create")
def render_create_page():
    app.logger.debug("Create")
    return flask.render_template('create.html')
    
@app.route("/_delete", methods=["POST"])
def delete():
    to_delete = []
    for memo_id in request.form:
        to_delete.append(memo_id)
    remove_memos(to_delete)
    return redirect("/index", 303)

@app.route("/_create", methods=["POST"])
def handle_create_request():
    date = request.form["Date"]
    memo = request.form["Memo"]
    insert_memo(date, memo)
    return redirect("/index", 303)

@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """
    try:
        then = arrow.get(date).to("US/Pacific")
        now = arrow.now("US/Pacific")
        print("Then: {} Now:{}".format(then, now))
        if then.date() == now.date():
            human = "Today"
        elif then.date() == now.replace(days=+1).date():
            human = "Tomorrow"
        elif then.date() == now.replace(days=-1).date():
            human = "Yesterday"
        else:
            human = then.humanize(now).capitalize()
            if human == "In a day":
                human = "Tomorrow"
            elif human == "A day ago":
                human = "Yesterday"
    except: 
        human = date
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, sorted by date, in a form that
    can be inserted directly in the 'session' object.
    """
    records = [ ]
    for record in collection.find( { "type": "dated_memo" } ):
        record['date'] = arrow.get(record['date']).replace(tzinfo=tz.gettz("US/Pacific")).isoformat()
        record['_id'] = str(record['_id'])
        records.append(record)
    return sorted(records, key=operator.itemgetter('date'))
    
def remove_memos(ids_to_remove):
    """
    Remove all memos whose IDs are contained in the list.
    
    ids_to_remove should be a list of hexadecimal object IDs, as strings
    """
    for id in ids_to_remove:
        collection.remove({"type":"dated_memo", "_id":ObjectId(id)})
        # We confirm the type is dated_memo, because otherwise users could
        # delete arbitrary objects from the database if they knew the IDs
        
def insert_memo(date, text):
    """
    Inserts a memo in the mongoDB memo database.
    
    "date" should be a date, as a string, formatted like yyyy-mm-dd.    
    "text" is the text of the memo.
    """
    datePattern = re.compile(r"\d\d\d\d-\d\d-\d\d")
    if datePattern.match(date):
        record = { "type": "dated_memo", 
                   "date": date,
                   "text": text
                 }
        collection.insert(record)


if __name__ == "__main__":
    # App is created above so that it will
    # exist whether this is 'main' or not
    # (e.g., if we are running in a CGI script)
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    # We run on localhost only if debugging,
    # otherwise accessible to world
    if CONFIG.DEBUG:
        # Reachable only from the same computer
        app.run(port=CONFIG.PORT)
    else:
        # Reachable from anywhere 
        app.run(port=CONFIG.PORT,host="0.0.0.0")

    
