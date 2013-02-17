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
import time
import logging
from threading import Thread, Event
from danbooru import Storage
from danbooru import DanbooruAPI
from danbooru.utils import default_dbpath, parse_query, retry_if_except
from danbooru.api import GelbooruAPI
from danbooru.error import DanbooruError
from danbooru.downloader import Downloader
import requests


class DaemonThread(Thread):

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.event = Event()
        self.loop_phrase = "new"

    def extraTags(self, tags, blacklist, whitelist):
        self.extra_tags = tags if tags else []
        self.extra_blacklist = blacklist if blacklist else []
        self.extra_whitelist = whitelist if whitelist else []

    def run(self):
        cfg = self.config
        dbname = cfg.loadValue('dbname', 'general', default_dbpath())
        db = Storage(dbname)
        sections = cfg.loadValue('fetch_from', 'general').split()
        wait_time = cfg.loadValue(('fetch_interval', int), 'general')
        while not self.event.is_set():
            for section in sections:
                logging.debug("Processing entry: %s", section)
                self.current_param = section
                host = cfg.loadValue('host', section)
                db.setHost(host, section)
                api_mode = cfg.loadValue('api_mode', section)
                if api_mode == 'danbooru':
                    board = DanbooruAPI(self.config.host)
                    login_info = cfg.loadValue(
                        ['login', 'password', 'salt'],
                        section
                    )
                    board.setLogin(**login_info)
                elif api_mode == 'gelbooru':
                    board = GelbooruAPI(host)
                else:
                    break
                self.current_phrase = 'metadata'
                default_tags = cfg.loadValue('default_tags', section)
                joined_tags = list(set(default_tags.split() + self.extra_tags))
                tags, query = parse_query(joined_tags)

                if len(tags) > cfg.loadValue(('max_tags', int), section):
                    logging.warning("Using more than %i tags, cutting down list", cfg.max_tags)
                    tags[:] = tags[:cfg.max_tags]

                blacklist = cfg.loadValue('blacklist', section)
                query['blacklist'] = list(set(blacklist.split() + self.extra_blacklist))
                whitelist = cfg.loadValue('whitelist', section)
                query['whitelist'] = list(set(whitelist.split() + self.extra_whitelist))
                limit = cfg.loadValue(('limit', int), section)
                for tag in tags:
                    self.current_param = tag
                    if self.event.is_set():
                        return
                    self.update(board, db, tag, query, section, limit)

            self.current_phrase = 'download'
            logging.debug("Starting download")
            self.downloadFiles(dbname)
            logging.debug("Download complete")

            #self.current_phrase = 'nepomuk'
            #self.run_nepomuk(cfg, dbname)

            self.current_phrase = 'wait'
            logging.debug("Waiting for %i seconds", wait_time)
            self.event.wait(wait_time)
        self.current_phrase = 'finished'

    def update(self, board, db, tag, query, section, limit):
        cfg = self.config
        fetch_mode = cfg.loadValue('fetch_mode', section)
        if fetch_mode == 'before_id':
            page_or_id = None
        elif fetch_mode in ['page', 'pid']:
            page_or_id = 1
        else:
            raise DanbooruError("Invalid fetch_mode: %s" % fetch_mode)

        while not self.event.is_set():
            post_list = retry_if_except(board.getPostsByType, tag, query, fetch_mode, page_or_id, limit, reraise=False)
            if post_list:
                start = time.time()
                results = db.savePosts(post_list)
                end = time.time() - start
                logging.debug("New entries: %i posts, %i images, %i tags", results['posts'], results['images'],
                              results['tags'])
                logging.debug("Time taken: %.2f seconds" % end)
                if not results['posts']:
                    logging.debug("Stopping since no new posts were inserted")
                    break
                if fetch_mode == 'before_id':
                    page_or_id = post_list[-1]['post_id']
                    logging.debug("Fetching posts below id: %i", page_or_id)
                elif fetch_mode in ['page', 'pid']:
                    page_or_id += 1
                    logging.debug('Fetching posts from page: %i', page_or_id)
            else:
                logging.debug('No posts returned')
                break

    def downloadFiles(self, dbname):
        def callback(file, current, total):
            if current == total:
                status = '[OK]           '
                endline = '\n'
            elif current > 0:
                status = '[DOWNLOADING]  '
                endline = '\r'
            else:
                status = '[ABORTED]      '
                endline = '\n'

            sys.stdout.write("%s: %i%% %s %s" % (
                os.path.basename(file),
                int(current * 100 / total),
                status,
                endline,
            ))
            sys.stdout.flush()

        dl_path = self.config.loadValue('download_path', 'general', 'danbooru')
        check_md5sum = self.config.loadValue(('check_md5sum', bool), 'default', False)

        dl = Downloader(dl_path, self.event)
        dl.downloadQueue(Storage(dbname), check_md5sum, callback)

    def pool(self, section):
        pass

    def nepomukTagging(self):
        from danbooru.nepomuk import NepomukTask
        nk = NepomukTask()
        dbname = self.config.loadValue('dbname', 'general', default_dbpath())
        dl_path = self.config.loadValue('download_path', 'general', 'danbooru')
        nk.updateDirectoryTags(dl_path, Storage(dbname))

    @property
    def status(self):
        return self.current_phrase, self.current_param

    def stop(self):
        self.event.set()
