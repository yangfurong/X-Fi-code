#!/usr/bin/env python3
import gpxpy
import gpxpy.gpx
import argparse
import os, sys
import re
import subprocess, shlex
from datetime import datetime, timezone
from .logger import logger

class _Coordinate(object):

    def __init__(self, lat, lon, elev, utc_ts, **kwargs):
        self.latitude = lat
        self.longitude = lon
        self.elevation = elev
        self.utc_ts = utc_ts
        self._attrs = {}
        for k, v in kwargs.items():
            self._attrs[k] = v

    def __getattr__(self, name):
        if name in self._attrs:
            return self._attrs[name]
        else:
            raise AttributeError("{} is not an attribute of the instance".format(name))

    def __str__(self):
        return "latitude {}, longitude {}, elevation {}, ts {}, attr {}".format(self.latitude, self.longitude, self.elevation, self.utc_ts, self._attrs)

class GPSParser(object):
    def __init__(self, gps_log):
        self._gps_log = gps_log

    def parse(self):
        """
        This function parses gpx files and return a list of coordinates
        """
        coords_list = []

        with open(self._gps_log, "r") as f:
            logger.info("[GPS]: Parsing {}".format(self._gps_log))

            gpx_reader = gpxpy.parse(f)
            for track in gpx_reader.tracks:
                for seg in track.segments:
                    for point in seg.points:
                        ts = point.time.replace(tzinfo=timezone.utc).timestamp()
                        coords_list.append(_Coordinate(point.latitude, point.longitude, point.elevation, ts))
        return coords_list

if __name__ == "__main__":
    parser = GPSParser(sys.argv[1])
    for row in parser.parse():
        print(row)
