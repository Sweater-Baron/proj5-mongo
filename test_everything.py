"""
Nose tests for flask_main.py
"""

import flask_main
import CONFIG
from pymongo import MongoClient
import arrow
from dateutil import tz  # For interpreting local times

try: 
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.memos
    collection = db.dated
except:
    print("Failure opening database. Is Mongo running? Correct password?")
    assert False; # So Nose says something went wrong
    sys.exit(1)

TEST_MEMO = {"type": "dated_memo",
                       "date": "2016-01-01",
                       "text": "Nosetest"
                      }
# pymongo will modify the contents of dictionaries that it's given as arguments.
# Thus, we need to give copies of TEST_MEMO to pymongo by referencing TEST_MEMO.copy()
    
def test_insert_memo():
    flask_main.insert_memo("2016-01-01", "Nosetest")
    assert collection.find_one(TEST_MEMO.copy())
    
def test_get_memos():
    collection.insert(TEST_MEMO.copy())
    collection.insert({"type": "dated_memo",
                       "date": TEST_MEMO['date'],
                       "text": "Nosetest2"
                      })
    memos = flask_main.get_memos()
    found_test_1 = False
    found_test_2 = False
    for memo in memos:
        if memo['date'] == arrow.get(TEST_MEMO.copy()['date']).replace(tzinfo=tz.gettz("US/Pacific")).isoformat():
            if memo['text'] == "Nosetest":
                found_test_1 = True
            elif memo['text'] == "Nosetest2":
                found_test_2 = True
    
    assert found_test_1 and found_test_2
    
def test_remove_memos():
    """
    remove_memos function should work. This also serves to clear out any test
    memos, so that none are left over after the nose test is run.
    """
    collection.insert(TEST_MEMO.copy())
    found = collection.find(TEST_MEMO.copy())
    found2 = collection.find({"type": "dated_memo",
                              "date": TEST_MEMO['date'],
                              "text": "Nosetest2"
                             })
    ids = []
    for cursor in (found, found2):
        for memo in cursor:
            ids.append(str(memo['_id']))
        
    flask_main.remove_memos(ids)
    assert not collection.find_one(TEST_MEMO.copy())
    assert not collection.find_one({"type": "dated_memo",
                                    "date": TEST_MEMO['date'],
                                    "text": "Nosetest2"
                                   })
def test_humanize_arrow_date():
    """
    Confirm that humanization won't be wonky (as long as the user is in the
    Pacific time zone)
    """
    today = arrow.now('US/Pacific').replace(hour=0, minute=0, second=0)
    days = {-1: "Yesterday", 0: "Today", 1: "Tomorrow"}
    for day in range(-1, 2):
        for hour in range(0, 24):
            test_date = today.replace(days=+day).replace(hours=+hour)
            print("Days: {} Hours: {}".format(day, hour))
            result = flask_main.humanize_arrow_date(test_date.isoformat())
            print(result)
            assert result == days[day]
            