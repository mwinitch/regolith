"""Helper for adding a to_do task to people.yml

"""
import datetime as dt
import dateutil.parser as date_parser
from dateutil.relativedelta import relativedelta
import sys

from regolith.helpers.basehelper import DbHelperBase
from regolith.fsclient import _id_key
from regolith.tools import (
    all_docs_from_collection,
    get_pi_id,
    document_by_value,
)

TARGET_COLL = "people"
ALLOWED_IMPORTANCE = [0, 1, 2]


def subparser(subpi):
    subpi.add_argument("description", help="the description of the to_do task. If the description has more than one "
                                           "word, please enclose it in quotation marks.",
                       default=None)
    subpi.add_argument("due_date",
                       help="Due date of the task. Either enter a date in format YYYY-MM-DD or an "
                            "integer. Integer 5 means 5 days from the "
                            "begin_date. "
                       )
    subpi.add_argument("-i", "--id", help="ID of the member to whom the task is assigned. The default id is saved in user.json. ")
    subpi.add_argument("-b", "--begin_date",
                       help="Begin date of the task in format YYYY-MM-DD. Default is today."
                       )
    subpi.add_argument("-d", "--duration",
                       help="The estimated duration the task will take in minutes. Default is 60 ",
                       default=60
                       )
    subpi.add_argument("-p", "--importance",
                       help=f"The importance of the task from {ALLOWED_IMPORTANCE}. Default is 1.",
                       default=1
                       )
    subpi.add_argument("-n", "--notes", nargs="+", help="Additional notes for this task. Each note should be enclosed "
                                                        "in quotation marks.")

    return subpi


class TodoAdderHelper(DbHelperBase):
    """Helper for adding a to_do task to people.yml
    """
    # btype must be the same as helper target in helper.py
    btype = "a_todo"
    needed_dbs = [f'{TARGET_COLL}']

    def construct_global_ctx(self):
        """Constructs the global context"""
        super().construct_global_ctx()
        gtx = self.gtx
        rc = self.rc
        if "groups" in self.needed_dbs:
            rc.pi_id = get_pi_id(rc)

        rc.coll = f"{TARGET_COLL}"
        rc.database = rc.databases[0]["name"]
        gtx[rc.coll] = sorted(
            all_docs_from_collection(rc.client, rc.coll), key=_id_key
        )
        gtx["all_docs_from_collection"] = all_docs_from_collection
        gtx["float"] = float
        gtx["str"] = str
        gtx["zip"] = zip

    def db_updater(self):
        rc = self.rc
        if not rc.id:
            try:
                rc.id = rc.default_user_id
            except AttributeError:
                print(
                    "Please set default_user_id in '~/.config/regolith/user.json', or you need to enter your group id "
                    "in the command line")
                return
        filterid = {'_id': rc.id}
        person = rc.client.find_one(rc.database, rc.coll, filterid)
        if not person:
            raise TypeError(f"The id {rc.id} can't be found in the people collection")
        now = dt.date.today()
        if not rc.begin_date:
            begin_date = now
        else:
            begin_date = date_parser.parse(rc.begin_date).date()
        try:
            relative_day = int(rc.due_date)
            due_date = begin_date + relativedelta(days=relative_day)
        except ValueError:
            due_date = date_parser.parse(rc.due_date).date()
        if begin_date > due_date:
            raise ValueError("begin_date can not be after due_date")
        importance = int(rc.importance)
        if importance not in ALLOWED_IMPORTANCE:
            raise ValueError(f"importance should be chosen from {ALLOWED_IMPORTANCE}")
        if not person.get("todos"):
            todolist = []
        else:
            todolist = person.get("todos")
        todolist.append({
            'description': rc.description,
            'due_date': due_date,
            'begin_date': begin_date,
            'duration': float(rc.duration),
            'importance': importance,
            'status': "started"})
        if rc.notes:
            todolist[-1]['notes'] = rc.notes

        rc.client.update_one(rc.database, rc.coll, {'_id': rc.id}, {"todos": todolist},
                             upsert=True)
        print(f"The task \"{rc.description}\" for {rc.id} has been added in {TARGET_COLL} collection.")

        return
