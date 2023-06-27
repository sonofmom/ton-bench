import os
import sys
import json
from Libraries.tools import general as gt
from Classes.Logger import Logger
from Classes.GracefulKiller import GracefulKiller

class AppConfig:
    def __init__(self, args):
        self.args = args
        self.log = Logger(args.verbosity)
        self.config = None
        self.ls_config = None
        self.gk = GracefulKiller()
        self.tmp = {}
        self.data = {
            "accounts": None
        }


        if hasattr(self.args, 'config_file'):
            fn = self.args.config_file
            self.log.log(self.__class__.__name__, 3, 'Config file {}'.format(fn))
            if not gt.check_file_exists(fn):
                self.log.log(self.__class__.__name__, 1, "Configuration file does not exist!")
                sys.exit(1)
            try:
                fh = open(fn, 'r')
                self.config = json.loads(fh.read())
                fh.close()
            except Exception as e:
                self.log.log(self.__class__.__name__, 1, "Configuration file read error: {}".format(str(e)))
                sys.exit(1)

            if "liteClient" in self.config:
                fn = self.config["liteClient"]["config"]
                self.log.log(self.__class__.__name__, 3, 'LS Config file {}'.format(fn))
                if not gt.check_file_exists(fn):
                    self.log.log(self.__class__.__name__, 1, "LS Configuration file does not exist!")
                    sys.exit(1)
                try:
                    fh = open(fn, 'r')
                    self.ls_config = json.loads(fh.read())
                    fh.close()
                except Exception as e:
                    self.log.log(self.__class__.__name__, 1, "LS Configuration file read error: {}".format(str(e)))
                    sys.exit(1)

            if "data" in self.config:
                if "accounts" in self.config["data"] and self.config["data"]["accounts"]:
                    self.data["accounts"] = {}
                    for element, value in self.config["data"]["accounts"].items():
                        self.log.log(self.__class__.__name__, 3, 'Reading in accounts data file {}'.format(value))
                        with open(value, 'r') as fh:
                            self.data["accounts"][element] = fh.read().split("\n")

                if "blocks" in self.config["data"] and self.config["data"]["blocks"]:
                    self.data["blocks"] = {}
                    for element, value in self.config["data"]["blocks"].items():
                        self.log.log(self.__class__.__name__, 3, 'Reading in blocks data file {}'.format(value))
                        self.data["blocks"][element] = []
                        with open(value, 'r') as fh:
                            for line in fh:
                                record = line.split(",")
                                self.data["blocks"][element].append([int(record[0]),int(record[1]),int(record[2])])

# end class
