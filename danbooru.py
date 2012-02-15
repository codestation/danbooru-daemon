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
from danbooru.api import Api
from danbooru.database import Database
from danbooru.settings import Settings
from danbooru.downloader import Downloader

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--config', dest='config', default='config.cfg',
            help='use the indicated config file')
    parser.add_argument('-t', '--tags', dest='tags',
            help='list of tags to use in search (join multiple "+")')
    parser.add_argument('-a', '--action', dest='action', required=True,
            help='set the action to perform')
    parser.add_argument('-b', '--before-id', dest='before_id', 
            help='search using this id as starting point')
    
    args = parser.parse_args()
    
    cfg = Settings(args.config)
    if not cfg.load('danbooru',['host', 'username', 'password', 'salt', 
                                'dbname', 'limit', 'download_path',
                                'log_level', 'log_file']):
        sys.exit(1)
        
    numeric_level = getattr(logging, cfg.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        logging.error('Invalid log_level in config: %s' % cfg.log_level)
        sys.exit(1)

    if cfg.log_file:        
        logging.basicConfig(filename=cfg.log_file, level=numeric_level)
    else:
        logging.basicConfig(level=numeric_level)

    board = Api(cfg.host, cfg.username, cfg.password, cfg.salt, cfg.dbname)

    limit = int(cfg.limit)
    tags = sys.argv[2]
    abort = False
    dl = None
    nk = None
    
    def signal_handler(signal, frame):
        global abort, dl, nk
        logging.info('Ctrl+C detected, shutting down...')
        abort = True
        if dl:
            dl.stopDownload()
        elif nk:
            nk.abortTask()

    signal.signal(signal.SIGINT, signal_handler)
    
    def getLastId(tags):
        if args.before_id:
            return int(args.before_id)
        else:
            posts = board.getPostsPage(tags, 1, 1)
            if not posts:
                logging.error('Error: cannot get last post id')
                sys.exit(1)
            return posts[0]['id'] + 1
    
    db = Database(cfg.dbname)
    
    if args.action == 'update':
        if not args.tags:
            logging.error('No tags specified. Aborting.')
            sys.exit(1)

        last_id = getLastId(args.tags)
        logging.debug('Fetching posts below id: %i' % last_id)
        while not abort:
            post_list = board.getPostsBefore(last_id, args.tags, limit)
            if post_list:
                result = db.addPosts(post_list)
                if len(result) > 1:
                    logging.debug('%i posts inserted, %i posts updated' % result)
                else:
                    logging.debug('%i posts inserted, no updates' % result)
                if result[0] == 0:
                    logging.debug('Stopping since no new posts were inserted')
                    break
                last_id = post_list[-1]['id']
                logging.debug('Fetching posts below id: %i' % last_id)
            else:
                logging.debug('No posts returned')
                break
            
    elif args.action == 'tags':
        last_id = getLastId()
        while not abort:
            tag_list = board.getTagsBefore(last_id, tags, limit)
            if tag_list:
                db.addTags(tag_list)
                last_id = tag_list[-1]['id']
                logging.debug('Next fetch id: %i' % last_id)
            else:
                break
        
    elif args.action == 'download':
        dl = Downloader(cfg.download_path)
        offset = 0
        while not abort:
            rows = db.getFiles(100, offset)
            if not rows:
                break
            dl.downloadQueue(rows)
            offset += 100
            
    elif args.action == 'nepomuk':
        from danbooru.nepomuk import NepomukTask
        nk = NepomukTask()
        nk.updateDirectoryTags(cfg.download_path, db)
