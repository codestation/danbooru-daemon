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

import sys
import signal
import argparse
import logging
import shutil
import re
from time import sleep
from os import listdir
from os.path import join, isdir, isfile, splitext
from danbooru.api import Api
from danbooru.database import Database
from danbooru.settings import Settings
from danbooru.downloader import Downloader


class Daemon(object):

    _stop = False
    abort_list = {}

    config_required = [
                       'host',
                       'username',
                       'password',
                       'salt',
                       'dbname',
                       ('limit', int),
                       'download_path',
                       'log_level',
                       'log_file',
                       'fetch_mode',
                       ('skip_file_check', bool),
                       ]

    config_optional = {
                       'default_tags': None,
                       'blacklist': None,
                       'whitelist': None,
                        ('max_tags', int): 2,
                    }

    def parseArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', dest='config', default='config.cfg',
                help='use the indicated config file')
        parser.add_argument('-s', '--section', dest='section', default='danbooru',
                help='select the section from the config file')
        parser.add_argument('-t', '--tags', dest='tags', nargs='+',
                help='list of tags to use in search')
        parser.add_argument('-b', '--blacklist', dest='blacklist', nargs='+',
                help='list of tags to skip in search')
        parser.add_argument('-w', '--whitelist', dest='whitelist', nargs='+',
                help='list of tags to always get in search')
        parser.add_argument('-a', '--action', dest='action', required=True,
                help='set the action to perform')
        parser.add_argument('-i', '--before-id', dest='before_id',
                help='search using this id as starting point')

        return parser.parse_args()

    def readConfig(self, config, section, required_fields, optional_fields):
        cfg = Settings(config)
        if not cfg.load(section, required_fields, optional_fields):
            sys.exit(1)

        if "log_level" in required_fields:
            numeric_level = getattr(logging, cfg.log_level.upper(), None)
            if not isinstance(numeric_level, int):
                logging.error('Invalid log_level in config: %s' % cfg.log_level)
                sys.exit(1)
            cfg.log_level = numeric_level
        return cfg

    def parseTags(self, args, cfg):
        # use default tags from file
        if cfg.default_tags:
            default_tags = [x.strip() for x in re.sub(' +', ' ', cfg.default_tags).split(' ')]
            if not args.tags: args.tags = []
            args.tags = args.tags + list(set(default_tags) - set(args.tags))

        if cfg.blacklist:
            blacklist_tags = [x.strip() for x in re.sub(' +',' ',cfg.blacklist).split(' ')]
            if not args.blacklist: args.blacklist = []
            args.blacklist = args.blacklist + list(set(blacklist_tags) - set(args.blacklist))

        if cfg.whitelist:
            whitelist_tags = [x.strip() for x in re.sub(' +',' ',cfg.whitelist).split(' ')]
            if not args.whitelist: args.whitelist = []
            args.whitelist = args.whitelist + list(set(whitelist_tags) - set(args.whitelist))

        # cut down the tag list if it have too much items
        max_tags_number = cfg.max_tags
        if args.tags and len(args.tags) > max_tags_number:
            logging.warning('Using more than %i tags, cutting down list' % max_tags_number)
            args.tags = args.tags[:max_tags_number]
            
    def abort(self):
        self._stop = True
        for k in self.abort_list.keys():
            self.abort_list[k].stop()
            
    def registerClassSignal(self, cls):
        self.abort_list[cls.__class__.__name__] = cls
        
    def unregisterClassSignal(self, cls):
        del self.abort_list[cls.__class__.__name__]
            
    def signalHandler(self, signal, frame): #@UnusedVariable
        logging.info('Ctrl+C detected, shutting down...')
        self.abort()

    def getLastId(self, tags, board, before_id=None):
        if before_id:
            return int(before_id)
        else:
            posts = board.getPostsPage(tags, 1, 1)
            if not posts:
                logging.error('Error: cannot get last post id')
                sys.exit(1)
            return posts[0]['id'] + 1      

    def main(self):
        args = self.parseArgs()
        cfg = self.readConfig(args.config, args.section, self.config_required, self.config_optional)

        logging.basicConfig(level=cfg.log_level, filename=cfg.log_file,
                            format='%(asctime)s %(levelname)s: %(message)s',
                            datefmt='%I:%M:%S %p')
        self.parseTags(args, cfg)
        signal.signal(signal.SIGINT, self.signalHandler)
        
        db = Database(cfg.dbname)
        db.setHost(cfg.host, args.section)
        
        if args.action == "daemon":
            self.run_daemon(args, db)
        elif args.action == "update":            
            board = Api(cfg.host, cfg.username, cfg.password, cfg.salt)
            self.run_update(args, cfg, board, db)
        elif args.action == "download":
            self.run_download(cfg, db)
        elif args.action == "nepomuk":
            self.run_nepomuk(cfg, db)
        elif args.action == "tags":            
            board = Api(cfg.host, cfg.username, cfg.password, cfg.salt)
            self.run_tags(args, db, board)
        elif args.action == "cleanup":
            self.cleanup(cfg, db, cfg.download_path)
            
    def run_daemon(self, args, db):
        cfg = self.readConfig(args.config, "default", ['fetch_from', ('fetch_interval', int)], [])
        
        if not cfg.fetch_from:
            logging.error('The fetch_from config option cannot be empty in daemon mode')
            sys.exit(1)
            
        if not cfg.fetch_interval:
            logging.error('The fetch_interval config option cannot be empty in daemon mode')
            sys.exit(1)

        sleep_time = cfg.fetch_interval
        sections = [x.strip() for x in cfg.fetch_from.split(' ')]

        while not self._stop:
            for section in sections:
                if self._stop: return
                cfg = self.readConfig(args.config, section, self.config_required, self.config_optional)
                db.setHost(cfg.host, section)                          
                board = Api(cfg.host, cfg.username, cfg.password, cfg.salt)
                logging.debug("Run upload mode for %s" % section)
                self.run_update(args, cfg, board, db)
                if self._stop: return
                logging.debug("Run download mode for %s" % section)
                self.run_download(cfg, db)
                if self._stop: return
                #logging.debug("Run nepomuk mode for %s" % section)
                #self.run_nepomuk(cfg, db)
                #if self._abort: break
            logging.debug("Waiting for %i seconds" % sleep_time)
            sleep(sleep_time)
    
    def run_update(self, args, cfg, board, db):
        if not args.tags:
            logging.error('No tags specified. Aborting.')
            sys.exit(1)

        if cfg.fetch_mode == "id":
            last_id = self.getLastId(args.tags, board, args.before_id)
            logging.debug('Fetching posts below id: %i' % last_id)
        elif cfg.fetch_mode == "page":
            page = 1
            logging.debug('Fetching posts from page: %i' % page)
        else:
            logging.error("Invalid fetch_mode")
            sys.exit(1)

        while not self._stop:
            if cfg.fetch_mode == "id":
                post_list = board.getPostsBefore(last_id, args.tags, cfg.limit, args.blacklist, args.whitelist)
            elif cfg.fetch_mode == "page":
                post_list = board.getPostsPage(args.tags, page, cfg.limit, args.blacklist, args.whitelist)

            if post_list:
                result = db.addPosts(post_list)
                if len(result) > 1:
                    logging.debug('%i posts inserted, %i posts updated' % result)
                else:
                    logging.debug('%i posts inserted, no updates' % result)
                if result[0] == 0:
                    logging.debug('Stopping since no new posts were inserted')
                    break
                if cfg.fetch_mode == "id":
                    last_id = post_list[-1]['id']
                    logging.debug('Fetching posts below id: %i' % last_id)
                elif cfg.fetch_mode == "page":
                    page += 1
                    logging.debug('Fetching posts from page: %i' % page)
            else:
                logging.debug('No posts returned')
                break
            
    def run_download(self, cfg, db):
        dl = Downloader(cfg.download_path)
        self.registerClassSignal(dl)
        offset = 0
        while not self._stop:
            rows = db.getFiles(100, offset)
            if not rows:
                break
            dl.downloadQueue(rows, cfg.skip_file_check)
            offset += 100
        self.unregisterClassSignal(dl)
            
    def run_nepomuk(self, cfg, db):
        from danbooru.nepomuk import NepomukTask
        nk = NepomukTask()
        self.registerClassSignal(nk)
        nk.updateDirectoryTags(cfg.download_path, db)
        self.unregisterClassSignal(nk)
            
    def run_tags(self, args, cfg, db, board):
        last_id = self.getLastId(args.tags, board, args.before_id)
        while not self._stop:
            tag_list = board.getTagsBefore(last_id, args.tags, cfg.limit)
            if tag_list:
                db.addTags(tag_list)
                last_id = tag_list[-1]['id']
                logging.debug('Next fetch id: %i' % last_id)
            else:
                break
            
    def clean_loop(self, directory, dest, db):
        for name in listdir(directory):
            if self._stop: break
            full_path = join(directory, name)
            if isdir(full_path):
                self.clean_loop(full_path, dest, db)
            elif isfile(full_path):
                md5 = splitext(name)[0]
                if not db.fileExists(md5):
                    logging.debug('%s isn\'t in database' % name)
                    shutil.move(full_path, join(dest, name))
            
    def cleanup(self, cfg, db, dest):
        self.clean_loop(cfg.download_path, dest, db)

if __name__ == '__main__':
    Daemon().main()
