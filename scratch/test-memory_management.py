#!/usr/bin/env python2

from pympler import tracker

tr = tracker.SummaryTracker()

# warm up
tr.print_diff()
tr.print_diff()
tr.print_diff()

print "START"

a = 1
tr.print_diff()
# simple objects are not counted

a = range(100)
tr.print_diff()
# lists are

del a
tr.print_diff()
# ok, not there anymore
