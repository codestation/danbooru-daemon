#!/usr/bin/python3
# -*- coding: utf-8 -*-

#   Copyright 2012 codestation
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import configparser


class Settings(object):

    def __init__(self, configfile):
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(configfile)

    def set_value(self, key, section):
        if isinstance(key, tuple):
            if key[1] == int:
                setattr(self, key[0], self.config.getint(section, key[0]))
            elif key[1] == bool:
                setattr(self, key[0], self.config.getboolean(section, key[0]))
            else:
                logging.warn("Unknown type: %s", key[1])
                setattr(self, key[0], self.config.get(section, key[0]))
        else:
            setattr(self, key, self.config.get(section, key))

    def load(self, section, required, optional):
        try:
            for key in required:
                try:
                    self.set_value(key, section)
                except configparser.NoOptionError:
                    self.set_value(key, "default")

            for key in optional:
                try:
                    self.set_value(key, section)
                except configparser.NoOptionError:
                    try:
                        self.set_value(key, "default")
                    except configparser.NoOptionError:
                        setattr(self, key, optional[key])

        except configparser.NoSectionError:
            logging.error('The section "%s" does not exist', section)
        except configparser.NoOptionError:
            logging.error('The value for "%s" is missing', key)
        else:
            return True
        return False
