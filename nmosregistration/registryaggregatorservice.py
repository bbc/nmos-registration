# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from nmoscommon.mdns import MDNSEngine
from nmoscommon.utils import getLocalIP
from nmosregistration.aggregation import AggregatorAPI, AGGREGATOR_APIVERSIONS
from nmoscommon.httpserver import HttpServer
from nmoscommon.logger import Logger
import signal
import time

import os
import json
import copy

import gevent
from gevent import monkey
monkey.patch_all()

HOST = getLocalIP()
SERVICE_PORT = 8235
DNS_SD_HTTP_PORT = 80
DNS_SD_HTTPS_PORT = 443
DNS_SD_NAME = 'registration_' + str(HOST)
DNS_SD_TYPE = '_nmos-register._tcp'
DNS_SD_LEGACY_TYPE = '_nmos-registration._tcp'
REGISTRY_PORT = 4001

class RegistryAggregatorService(object):
    def __init__(self, logger=None, interactive=False):
        self.config      = {"priority": 0, "https_mode": "disabled", "enable_mdns": True}
        self._load_config()
        self.running     = False
        self.httpServer  = None
        self.interactive = interactive
        self.mdns        = MDNSEngine()
        self.logger      = Logger("aggregation", logger)

    def _load_config(self):
        try:
            # Check for current nmos config file and legacy ipstudio file
            nmos_config_file = "/etc/nmos-registration/config.json"
            ipstudio_config_file = "/etc/ips-regaggregator/config.json"
            if os.path.isfile(nmos_config_file):
                f = open(nmos_config_file, 'r')
            elif os.path.isfile(ipstudio_config_file):
                f = open(ipstudio_config_file, 'r')
            if f:
                extra_config = json.loads(f.read())
                self.config.update(extra_config)
        except Exception as e:
            print("Exception loading config: {}".format(e))

    def start(self):
        if self.running:
            gevent.signal(signal.SIGINT,  self.sig_handler)
            gevent.signal(signal.SIGTERM, self.sig_handler)

        self.mdns.start()

        self.httpServer = HttpServer(AggregatorAPI, SERVICE_PORT, '0.0.0.0', api_args=[self.logger, self.config])
        self.httpServer.start()
        while not self.httpServer.started.is_set():
            print('Waiting for httpserver to start...')
            self.httpServer.started.wait()

        if self.httpServer.failed is not None:
            raise self.httpServer.failed

        print("Running on port: {}".format(self.httpServer.port))

        self._advertise_mdns()

    def _advertise_mdns(self):
        priority = self.config["priority"]
        if not str(priority).isdigit():
            priority = 0

        if self.config["https_mode"] != "enabled" and self.config["enable_mdns"]:
            self.mdns.register(DNS_SD_NAME + "_http", DNS_SD_TYPE, DNS_SD_HTTP_PORT,
                               self._mdns_txt(priority, AGGREGATOR_APIVERSIONS, "http"))
            if self._require_legacy_mdns():
                # Send out deprecated advertisement
                self.mdns.register(DNS_SD_NAME + "_http_dep", DNS_SD_LEGACY_TYPE, DNS_SD_HTTP_PORT,
                                   self._mdns_txt(priority, AGGREGATOR_APIVERSIONS, "http"))

        if self.config["https_mode"] != "disabled" and self.config["enable_mdns"]:
            self.mdns.register(DNS_SD_NAME + "_https", DNS_SD_TYPE, DNS_SD_HTTPS_PORT,
                               self._mdns_txt(priority, AGGREGATOR_APIVERSIONS, "https"))
            if self._require_legacy_mdns():
                # Send out deprecated advertisement
                self.mdns.register(DNS_SD_NAME + "_https_dep", DNS_SD_LEGACY_TYPE, DNS_SD_HTTPS_PORT,
                                   self._mdns_txt(priority, AGGREGATOR_APIVERSIONS, "https"))

    def _require_legacy_mdns(self):
        legacy_apiversions = ["v1.0", "v1.1", "v1.2"]
        for api_ver in AGGREGATOR_APIVERSIONS:
            if api_ver in legacy_apiversions:
                return True
        return False

    def _mdns_txt(self, priority, versions, protocol):
        return {"pri": priority, "api_ver": ",".join(versions), "api_proto": protocol}

    def run(self):
        self.running = True
        self.start()
        while self.running:
            time.sleep(1)
        self._cleanup()

    def _cleanup(self):
        self.mdns.stop()
        self.mdns.close()
        self.httpServer.stop()
        print("Stopped main()")

    def stop(self):
        self.running = False

    def sig_handler(self):
        print('Pressed ctrl+c')
        self.stop()
