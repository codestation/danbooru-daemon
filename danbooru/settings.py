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

import configparser
import logging

class Settings(object):
    
    def __init__(self, configfile):    
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(configfile)
    
    def load(self, section, required, optional):
        try:
            for key in required:
                try:
                    setattr(self, key, self.config.get(section, key))
                except configparser.NoOptionError:
                    setattr(self, key, self.config.get('default', key))
                    
            for key in optional:
                try:
                    setattr(self, key, self.config.get(section, key))
                except configparser.NoOptionError:
                    try:
                        setattr(self, key, self.config.get('default', key))
                    except configparser.NoOptionError:
                        setattr(self, key, optional[key])

        except configparser.NoSectionError:
            logging.error('The section "%s" does not exist' % section)
        except configparser.NoOptionError:
            logging.error('The value for "%s" is missing' % key)
        else:
            return True
        return False