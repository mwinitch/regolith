"""Builder for websites."""
import os
from itertools import groupby

from regolith.tools import all_docs_from_collection, date_to_float, date_to_rfc822, \
    rfc822now


doc_date_key = lambda x: date_to_float(x.get('year', 1970), x.get('month', 'jan'))
ene_date_key = lambda x: date_to_float(x.get('end_year', 1970), x.get('end_month', 'jan'))
category_val = lambda x: x.get('category', '<uncategorized>')
level_val = lambda x: x.get('level', '<no-level>')
id_key = lambda x: x.get('_id', '')

def date_key(x):
    if 'end_year' in x:
        v = date_to_float(x['end_year'], x.get('end_month', 'jan'), x.get('end_day', 0))
    elif 'year' in x:
        v = date_to_float(x['year'], x.get('month', 'jan'), x.get('day', 0))
    elif 'begin_year' in x:
        v = date_to_float(x['begin_year'], x.get('begin_month', 'jan'), 
                                           x.get('begin_day', 0))
    else:
        raise KeyError('could not find year in ' + str(x))
    return v

POSITION_LEVELS = {
    '': -1,
    'undergraduate research assistant': 1,
    'graduate research assistant': 2,
    'research assistant': 2,
    'post-doctoral scholar': 3,
    'assistant scientist': 4,
    'research scientist': 4.5,
    'associate scientist': 5,
    'research associate': 5, 
    'ajunct professor': 5,
    'programer': 5,
    'programmer': 5,
    'visiting scientist': 6,
    'research assistant professor': 7,
    'assistant professor': 8,
    'associate professor': 9,
    'professor emeritus': 9,
    'professor': 10,
    }

def position_key(x):
    """Sorts a people based on thier position in the research group."""
    pos = x.get('position', '').lower()
    return POSITION_LEVELS.get(pos, -1)

