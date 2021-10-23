#!/usr/bin/env python3

from datetime import timedelta
import functools

tlist = [(11,18,8), (12,48,29), (32,38,6), (167, 40, 38)]

deltas = [timedelta(hours=x[0], minutes=x[1], seconds=x[2]) for x in tlist]

print(functools.reduce(lambda x,y: x+y, deltas))
