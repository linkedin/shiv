# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "python-dateutil",
#   "rich",
# ]
# ///

# Code from https://pypi.org/project/python-dateutil/
# Description:
# Suppose you want to know how much time is left, in years/months/days/etc,
# before the next easter happening on a year with a Friday 13th in August,
# and you want to get today’s date out of the “date” unix system command.

from dateutil.relativedelta import relativedelta, FR
from dateutil.easter import easter
from dateutil.rrule import rrule, YEARLY
from dateutil.parser import parse
from rich.pretty import pprint

now = parse("Sat Oct 11 17:13:46 UTC 2003")
today = now.date()
year = rrule(YEARLY, dtstart=now, bymonth=8, bymonthday=13, byweekday=FR)[0].year
rdelta = relativedelta(easter(year), today)

pprint(f"Today is: {today}")
pprint(f"Year with next Aug 13th on a Friday is: {year}")
pprint(f"How far is the Easter of that year: {rdelta}")
pprint(f"And the Easter of that year is: {today+rdelta}")
