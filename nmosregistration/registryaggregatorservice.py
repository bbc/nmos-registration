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

import gevent
from gevent import monkey
monkey.patch_all()

from nmoscommon.mdns import MDNSEngine # noqa E402
from nmoscommon.utils import getLocalIP # noqa E402
from nmosregistration.aggregation import AggregatorAPI, AGGREGATOR_APIVERSIONS # noqa E402
from nmoscommon.httpserver import HttpServer # noqa E402
from nmoscommon.logger import Logger # noqa E402
from .config import config # noqa E402
import signal # noqa E402
import time # noqa E402

# Handle if systemd is installed instead of newer cysystemd
try:
    from cysystemd import daemon # noqa E402
    SYSTEMD_READY = daemon.Notification.READY
except ImportError:
    from systemd import daemon # noqa E402
    SYSTEMD_READY = "READY=1"

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
        self.config = config
        self.running = False
        self.httpServer = None
        self.interactive = interactive
        self.mdns = MDNSEngine()
        self.logger = Logger("aggregation", logger)

    def start(self):
        if self.running:
            gevent.signal(signal.SIGINT, self.sig_handler)
            gevent.signal(signal.SIGTERM, self.sig_handler)

        self.mdns.start()

        self.httpServer = HttpServer(AggregatorAPI, SERVICE_PORT, '0.0.0.0', api_args=[self.logger, self.config])
        self.httpServer.start()
        while not self.httpServer.started.is_set():
            print("Waiting for httpserver to start...")
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
        daemon.notify(SYSTEMD_READY)
        while self.running:
            time.sleep(1)

    def _cleanup(self):
        self.mdns.close()
        self.httpServer.stop()
        print("Stopped main()")

    def stop(self):
        self.running = False
        self._cleanup()

    def sig_handler(self):
        print("Pressed ctrl+c")
        self.stop()


if __name__ == '__main__':
    service = RegistryAggregatorService()
    service.run()
