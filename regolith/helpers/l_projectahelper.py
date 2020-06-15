"""Helper for listing upcoming (and past) projectum milestones.

   Projecta are small bite-sized project quanta that typically will result in
   one manuscript.
"""
import datetime as dt
import dateutil.parser as date_parser
from dateutil.relativedelta import relativedelta
import sys

from regolith.dates import get_due_date, get_dates
from regolith.helpers.basehelper import SoutHelperBase
from regolith.fsclient import _id_key
from regolith.tools import (
    all_docs_from_collection,
    get_pi_id,
)

TARGET_COLL = "projecta"
HELPER_TARGET = "l_projecta"
ALLOWED_STATI = ["proposed", "started", "finished", "back_burner", "paused", "cancelled"]


def subparser(subpi):
    subpi.add_argument("-v", "--verbose", action="store_true", help='increase verbosity of output')
    subpi.add_argument("-l", "--lead",
                       help="Filter milestones for this project lead"
                       )
    subpi.add_argument("-p", "--person",
                       help="Filter milestones for this person whether lead or not"
                       )
    subpi.add_argument("-s", "--stati", nargs="+",
                       help=f"List of stati for the project that you want returned,"
                            f"from {ALLOWED_STATI}.  Default is proposed and started"
                       )
    subpi.add_argument("-e", "--ended", action="store_true",
                       help="Lists projects that have ended. Use the -d and -r flags to specify"
                            "from one date and how many days"
                       )
    subpi.add_argument("-d", "--date",
                       help="projecta with end_date within RANGE before this date will be listed."
                            "Default is today"
                       )
    subpi.add_argument("-r", "--range",
                       help="date range back from DATE to search over in days. If no "
                            "range is specified, search will be 7 days"
                       )
    return subpi


class ProjectaListerHelper(SoutHelperBase):
    """Helper for listing upcoming (and past) projectum milestones.

       Projecta are small bite-sized project quanta that typically will result in
       one manuscript.
    """
    # btype must be the same as helper target in helper.py
    btype = HELPER_TARGET
    needed_dbs = [f'{TARGET_COLL}']

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
        if rc.date:
            desired_date = date_parser.parse(rc.date).date()
        else:
            desired_date = dt.date.today()

        if rc.range:
            num_of_days = int(rc.range)
        else:
            num_of_days = 7

        bad_stati = ["finished", "cancelled", "paused", "back_burner"]
        projecta = []
        end_projecta = []
        if rc.lead and rc.person:
            raise RuntimeError(f"please specify either lead or person, not both")
        for projectum in self.gtx["projecta"]:
            if isinstance(projectum.get('group_members'), str):
                projectum['group_members'] = [projectum.get('group_members')]
            if rc.lead and projectum.get('lead') != rc.lead:
                continue
            if rc.person:
                if isinstance(rc.person, str):
                    rc.person = [rc.person]
                good_p = []
                for i in rc.person:
                    if projectum.get('lead') == rc.person:
                        good_p.append(i)
                    if projectum.get('group_members') and i in projectum.get('group_members'):
                        good_p.append(i)
                if len(good_p) == 0:
                    continue
            if not rc.ended and not rc.stati and projectum.get('status') in bad_stati:
                continue
            if rc.stati and projectum.get('status') not in rc.stati:
                continue
            if rc.ended and not projectum.get('end_date'):
                continue
            if rc.ended:
                end_date = projectum.get('end_date')
                if isinstance(end_date, str):
                    end_date = date_parser.parse(end_date).date()
                low_range = desired_date - dt.timedelta(days=num_of_days)
                high_range = desired_date + dt.timedelta(days=num_of_days)
                if low_range <= end_date <= high_range:
                    end_projecta.append(projectum)
                    continue
            projecta.append(projectum["_id"])

        if rc.ended:
            for p in end_projecta:
                mems = p.get("group_members")
                collabs = p.get("collaborators")
                print("{}    {}\n"
                      "    Lead: {}    Members: {}    Collaborators: {}".format(p.get("_id"),
                                                                                p.get("description"),
                                                                                p.get("lead"),
                                                                                ', '.join(mems) if mems else mems,
                                                                                ', '.join(
                                                                                    collabs) if collabs else collabs))
        projecta.sort()
        for i in projecta:
            print(i)
        return
