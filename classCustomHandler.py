"""
Module with class for custom logger
Could be used by many of IG API related app
"""

import time
import re

import os
import glob

import logging
import logging.handlers

try:
    import codecs
except ImportError:
    codecs = None


class CustomTimedRotatingFileHandler(logging.handlers.
                                     TimedRotatingFileHandler):

    """
    Custom TimedRotatingFileHandler, as the name of log created
    in base class in not convenient(an extension is appended to
    the base file name). Subclass getFilesToDelete as we change
    of log file. Looks complicated for a simple goal
    """

    def __init__(self, prefix, when, backupCount):

        """
        :param prefix: string, prefix for log file, MUST contains "-"
                       otherwise the regex line 81 MUST be changed

        :param when: frequency of rotation, not working if script
                     not running continuously
        """

        if when == "S":
            suffix = "%Y-%m-%d_%H-%M-%S"
        elif when == "M":
            suffix = "%Y-%m-%d_%H-%M"
        elif when == "H":
            suffix = "%Y-%m-%d_%H"
        elif when == "D" or when == "MIDNIGHT":
            suffix = "%Y-%m-%d"
        elif when.startswith("W"):
            suffix = "%Y-%m-%d"
        else:
            raise ValueError("Invalid rollover interval specified: %s"
                             % self.when)

        self.prefix  = prefix
        self.dir_log = os.getcwd() + "/Logs/"

        # dir_log here MUST be with os.sep on the end
        filename = self.dir_log + self.prefix + time.strftime(suffix) + ".log"
        log_files = glob.glob(self.dir_log+"*.log")

        logging.handlers\
               .TimedRotatingFileHandler.__init__(self,
                                                  filename,
                                                  when=when,
                                                  backupCount=backupCount)

        """
        If we doRollover at each start it delete content of
        current day log file. So check if file name is not in
        log_files (first start of current day) and doRollOVer
        """

        try:
            if filename not in log_files:
                self.doRollover()
        except Exception:
            pass


    def getFilesToDelete(self):

        """Reimplement base method. Change the way it found file to delete"""

        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []

        # get the string before the date
        prefix = re.match(r"(\w)*(-)", baseName).group()
        plen = len(prefix)

        for fileName in fileNames:

            # fileName = os.path.splitext(fileName)[0]
            ext    = os.path.splitext(fileName)[1]
            extlen = len(ext)

            if fileName[:plen] == prefix:
                suffix = fileName[plen:-extlen]

                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()

        if len(result) < self.backupCount:
            result = []
        else:
            result = result[:len(result) - self.backupCount]

        return result


    def doRollover(self):

        """
        Found on internet did not spend time on to understand it, just
        changed the way we build the baseFilename according to suffix
        """

        self.stream.close()

        # get the time that this sequence started at and make it a TimeTuple
        t = self.rolloverAt - self.interval
        timeTuple = time.localtime(t)

        self.baseFilename = self.dir_log + self.prefix +\
                            time.strftime(self.suffix) + ".log"
        if self.encoding:
            self.stream = codecs.open(self.baseFilename, "w", self.encoding)
        else:
            self.stream = open(self.baseFilename, "w")

        self.rolloverAt = self.rolloverAt + self.interval
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
