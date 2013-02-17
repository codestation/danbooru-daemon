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

import os
import sys
import signal
import shutil
import logging
import argparse

from danbooru import Settings
from danbooru.daemon import DaemonThread
from danbooru.utils import default_dbpath
from danbooru.db import Storage


class Daemon(object):

    CFG_FILE = ".danbooru-daemon.cfg"

    def parseArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', dest='config',
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

    def signalHandler(self, signal, frame):  # @UnusedVariable
        logging.info("Ctrl+C detected, shutting down...")
        if hasattr(self, 'daemon_thread'):
            self.daemon_thread.stop()

    def main(self):
        # load command-line arguments
        cmd_args = self.parseArgs()

        # load settings from file
        user_dir = os.path.expanduser("~")
        configfile = cmd_args.config or os.path.join(user_dir, self.CFG_FILE)
        config = Settings(configfile)

        # load log level from config file
        try:
            logging.basicConfig(
                level=config.loadValue('log_level', 'general', logging.INFO),
                filename=config.loadValue('log_file', 'general', None),
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%I:%M:%S %p'
            )
        except TypeError:
            logging.error("Invalid log_level in config: %s" % config.log_level)
            sys.exit(1)

        #install signal handler for CTRL+C
        signal.signal(signal.SIGINT, self.signalHandler)

        if cmd_args.action == 'daemon':
            self.daemon_thread = DaemonThread(config)
            self.daemon_thread.extraTags(cmd_args.tags, cmd_args.blacklist, cmd_args.whitelist)
            self.daemon_thread.start()
            self.daemon_thread.join()
            logging.debug("Thread finished")
        elif cmd_args.action == 'download':
            dbname = config.loadValue('dbname', 'general', default_dbpath())
            DaemonThread(config).downloadFiles(dbname)
        elif cmd_args.action == 'pool':
            pass
        elif cmd_args.action == 'cleanup':
            self.cleanup(config, cmd_args.blacklist, cmd_args.whitelist)
        else:
            logging.error("Not implemented: %s", cmd_args.action)
            sys.exit(1)

    def run_tags(self, args, cfg, db, board):  # @UnusedVariable
        last_id = self.getLastId(args.tags, board, args.before_id)
        while not self._stop:
            tagList = board.getTagsBefore(last_id, args.tags, cfg.limit)
            if tagList:
                #FIXME: implement addTags
                #db.addTags(tagList)
                last_id = tagList[-1]['id']
                logging.debug('Next fetch id: %i' % last_id)
            else:
                break

    def run_pools(self, db, board):
        page = 1
        while not self._stop:
            logging.debug('Fetching pools from page: %i', page)
            poolList = board.getPoolsPage(page)
            if poolList:
                created, updated, up_to_date = db.savePools(poolList)
                if up_to_date:
                    logging.debug('Pool list up-to-date, %i new, %i updated', created, updated)
                    break
                page += 1
            else:
                break

    def run_pool_posts(self, db, board):
        offset = 0
        limit = 1000
        pools = list()
        while not self._stop:
            pools_data = db.getPools(limit, offset)
            if not pools_data:
                break
            pools += [x.pool_id for x in pools_data]
            offset += limit
            logging.debug('Building pool list: %i...', offset)
        logging.debug('Fetching posts from %i pools', len(pools))
        for pool in pools:
            page = 1
            count = 0
            total = 0
            while not self._stop:
                logging.debug('Fetching from pool: %i, posts from page: %i', pool, page)
                posts = board.getPoolPostsPage(pool, page)
                if posts:
                    if page == 1:
                        db.savePool(pool, posts_id=None, modified=True)
                    count += db.savePool(pool, posts, modified=True)
                    page += 1
                    total += len(posts)
                else:
                    count += db.savePool(pool)
                    logging.debug('Got %i/%i posts from pool %i', count, total, pool)
                    break

    def clean_loop(self, directory, dest, db):
        count = 0
        for name in os.listdir(directory):
            full_path = os.path.join(directory, name)
            if os.path.isdir(full_path):
                count += self.clean_loop(full_path, dest, db)
            elif os.path.isfile(full_path):
                md5 = os.path.splitext(name)[0]
                if not db.fileExists(md5):
                    logging.debug('%s isn\'t in database', name)
                    shutil.move(full_path, os.path.join(dest, name))
                    count += 1
        return count

    def cleanup(self, cfg, extra_blacklist, extra_whitelist):
        dbname = cfg.loadValue('dbname', 'general', default_dbpath())
        db = Storage(dbname)
        blacklist = cfg.loadValue('blacklist', 'default')
        if extra_blacklist:
            blacklist = list(set(blacklist.split() + extra_blacklist))
        else:
            blacklist = blacklist.split()
        whitelist = cfg.loadValue('whitelist', 'default')
        if extra_whitelist:
            whitelist = list(set(whitelist.split() + extra_whitelist))
        else:
            whitelist = whitelist.split()
        post_c, img_c, tag_c = db.deletePostsByTags(blacklist, whitelist)
        logging.debug('Deleted %i posts, %i images refs, %i tags', post_c, img_c, tag_c)

        dl_path = cfg.loadValue('download_path', 'general')
        count = self.clean_loop(dl_path, dl_path, db)
        logging.debug('Moved %i images', count)

if __name__ == '__main__':
    Daemon().main()
