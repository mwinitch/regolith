"""Helper for listing the to-do tasks. Tasks are gathered from people.yml, milestones, and group meeting actions.

"""
import datetime as dt
import dateutil.parser as date_parser
import sys
from dateutil.relativedelta import *

from regolith.dates import get_due_date, get_dates
from regolith.helpers.basehelper import SoutHelperBase
from regolith.fsclient import _id_key
from regolith.tools import (
    all_docs_from_collection,
    get_pi_id,
    document_by_value,
)

TARGET_COLL = "people"
TARGET_COLL2 = "projecta"
TARGET_COLL3 = "meetings"
HELPER_TARGET = "l_todo"
Importance = [0, 1, 2]
ALLOWED_STATI = ["started", "finished"]


def subparser(subpi):
    subpi.add_argument("-v", "--verbose", action="store_true",
                       help='increase verbosity of output')
    subpi.add_argument("-i", "--id",
                       help=f"Filter to-do tasks for this user id. Default is saved in user.json."
                       )
    subpi.add_argument("-s", "--short_tasks", nargs='?', const=30,
                       help='Filter tasks with estimated duration <= 30 mins, but if a number is specified, the duration of the filtered tasks will be less than that number of minutes.')
    return subpi


class TodoListerHelper(SoutHelperBase):
    """Helper for listing the to-do tasks. Tasks are gathered from people.yml, milestones, and group meeting actions.
    """
    # btype must be the same as helper target in helper.py
    btype = HELPER_TARGET
    needed_dbs = [f'{TARGET_COLL}', f'{TARGET_COLL2}', f'{TARGET_COLL3}']

    def construct_global_ctx(self):
        """Constructs the global context"""
        super().construct_global_ctx()
        gtx = self.gtx
        rc = self.rc
        if "groups" in self.needed_dbs:
            rc.pi_id = get_pi_id(rc)
        rc.coll = f"{TARGET_COLL}"
        try:
            if not rc.database:
                rc.database = rc.databases[0]["name"]
        except:
            pass
        colls = [
            sorted(
                all_docs_from_collection(rc.client, collname), key=_id_key
            )
            for collname in self.needed_dbs
        ]
        for db, coll in zip(self.needed_dbs, colls):
            gtx[db] = coll
        gtx["all_docs_from_collection"] = all_docs_from_collection
        gtx["float"] = float
        gtx["str"] = str
        gtx["zip"] = zip

    def sout(self):
        rc = self.rc
        if not rc.id:
            try:
                rc.id = rc.default_user_id
            except AttributeError:
                print(
                    "Please set default_user_id in '~/.config/regolith/user.json',\
                     or you need to enter your group id in the command line")
                return

        # find fisrt name in people.yml:
        try:
            person = document_by_value(all_docs_from_collection(rc.client, "people"), "_id", rc.id)
            first_name = person["name"].split()[0]
        except TypeError:
            print(
                "The id you entered can't be found in people.yml.")
            return

        # gather to-do tasks in people.yml
        try:
            todolist_tasks = document_by_value(all_docs_from_collection(rc.client, "people"), "_id", rc.id)
            gather_todos = todolist_tasks["todos"]
        # if there is no document with this id or that id doesn't have the key "todos" in people.yml:
        except:
            gather_todos = []

        # gather to-do tasks in projecta.yml
        for projectum in self.gtx["projecta"]:
            if projectum.get('lead') != rc.id:
                continue
            projectum["deliverable"].update({"name": "deliverable"})
            gather_miles = [projectum["kickoff"], projectum["deliverable"]]
            gather_miles.extend(projectum["milestones"])
            for ms in gather_miles:
                if projectum["status"] not in ["finished", "cancelled"]:
                    if ms.get('status') not in \
                            ["finished", "cancelled"]:
                        due_date = get_due_date(ms)
                        ms.update({
                            'id': projectum.get('_id'),
                            'due_date': due_date,
                        })
                        ms.update({'description': f'{ms.get("id")}, {ms.get("name")}'})

                        gather_todos.append(ms)

        mtgs = []
        for mtg in self.gtx["meetings"]:
            mtg['date']=get_dates(mtg)["date"]
            if len(list(mtg.get('actions'))) != 0:
                mtgs.append(mtg)
        if len(mtgs) > 0:
            mtgs = sorted(mtgs, key=lambda x: x.get('date'), reverse=True)
            actions = mtgs[0].get('actions')

            due_date = mtgs[0].get('date') + relativedelta(weekday=TH)
            for a in actions:
                ac = a.casefold()
                if "everyone" in ac or "all" in ac or first_name.casefold() in ac:
                    gather_todos.append({
                        'description': a,
                        'due_date': due_date,
                        'status': 'started'
                    })

        num = 0

        for item in gather_todos:
            if item.get('importance') is None:
                item['importance'] = 1
            if type(item["due_date"]) == str:
                item["due_date"] = date_parser.parse(item["due_date"]).date()

        gather_todos = sorted(gather_todos, key=lambda k: (k['due_date'], -k['importance']))

        if rc.short_tasks:
            for t in gather_todos[::-1]:
                if t.get('duration') is None or float(t.get('duration')) > float(rc.short_tasks):
                    gather_todos.remove(t)

        if rc.verbose:
            for t in gather_todos:
                if t.get('status') not in ["finished", "cancelled"]:
                    print(
                        f"{num + 1}. {t.get('description')}")
                    if t.get('notes') :
                        print(f"     --notes: {t.get('notes')}")
                    print(f"     --due: {t.get('due_date')}, importance:{t.get('importance')},",
                          f"{t['duration']} min," if 'duration' in t else "",
                          f"start date: {t['begin_date']}" if 'begin_date' in t else "")
                    # use many if Statements, so duration or begin_date won't be printed if they are unassigned.

                    num += 1
            # print finished tasks:
            for t in todolist_tasks["todos"]:
                if t.get('status') == "finished":
                    print(
                        f"finished: {t.get('description')}")
                    if t.get('notes'):
                        print(f"     --notes: {t.get('notes')}")
                    print(f"     --due: {t.get('due_date')}, importance:{t.get('importance')},",
                          f"{t['duration']} min," if 'duration' in t else "",
                          f"start date: {t['begin_date']}" if 'begin_date' in t else ""
                          f"end date: {t['end_date']}" if 'end_date' in t else "")
                    # use many if Statements, so duration or begin_date won't be printed if they are unassigned.


        else:
            for t in gather_todos:
                if t.get('status') not in ["finished", "cancelled"]:
                    print(f"{num + 1}. {t.get('description')}")
                    num += 1

        return
