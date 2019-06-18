# Copyright 2019 British Broadcasting Corporation
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

from six import text_type

import unittest
import uuid
import copy
import requests
from couchbase.cluster import Cluster, PasswordAuthenticator
import os
import time
from testcontainers.compose import DockerCompose
from testcontainers.core.container import DockerContainer
from . import util

from nmosregistration.registryaggregatorservice import RegistryAggregatorService
from nmosregistration.couchbase_backend import CouchbaseInterface

bucket_name = 'nmos-test'
test_username = 'nmos-test'
test_password = 'password'

def _initialise_cluster(host, port, bucket, username, password):
    # Initialize node
    requests.post('http://{0}:{1}/nodes/self/controller/settings'.format(host,port),
        auth=('Administrator', 'password'),
        data={
            'path': '/opt/couchbase/var/lib/couchbase/data',
            'index_path': '/opt/couchbase/var/lib/couchbase/data',
            'cbas_path': '/opt/couchbase/var/lib/couchbase/data'
        }
    )
    # Rename node
    requests.post('http://{0}:{1}/node/controller/rename'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'hostname': '127.0.0.1'
        }
    )
    # Setup services
    requests.post('http://{0}:{1}/node/controller/setupServices'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'services': 'kv,index,n1ql,fts'
        }
    )
    # Setup admin username/password
    requests.post('http://{0}:{1}/settings/web'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'password': 'password',
            'username': 'nmos-test',
            'port': 8091
        }
    )
    # Build bucket
    requests.post('http://{0}:{1}/pools/default/buckets'.format(host,port),
        auth=requests.auth.HTTPBasicAuth(username, password),
        data={
            'flushEnabled': 1,
            'replicaNumber': 1,
            'evictionPolicy': 'valueOnly',
            'ramQuotaMB': 2048,
            'bucketType': 'couchbase',
            'name': bucket_name
        }
    )

class SubmissionRoutingTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):

        self.couch_container = DockerCompose('{}/tests/'.format(os.getcwd()))
        self.couch_container.start()
        self.couch_container.wait_for('http://localhost:8091')

        host = self.couch_container.get_service_host('couchbase', 8091)
        port = self.couch_container.get_service_port('couchbase', 8091)
        
        _initialise_cluster(host, port, bucket_name, test_username, test_password)
        
        time.sleep(2) # TODO, properly wait for setup somehow

        self.registry = RegistryAggregatorService(registry={
            "type": "couchbase",
            "hosts": [host],
            "port": port,
            "username": test_username,
            "password": test_password,
            "bucket": bucket_name
        })
        self.registry.start()

        cluster = Cluster('couchbase://{}'.format(host))
        auth = PasswordAuthenticator(test_username, test_password)
        cluster.authenticate(auth)
        self.test_bucket = cluster.open_bucket(bucket_name)

    def test_write(self):
        # TODO, make cluster a class variable? Set up in setUpClass and pass around?
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        requests.post('http://0.0.0.0:8235/x-nmos/registration/v1.2/resource', json=request_payload)
        time.sleep(2)
        stored = self.test_bucket.get(doc_body['id'])
        self.assertDictEqual(stored.value, doc_body)

    def tearDown(self):
        self.test_bucket.flush()

    @classmethod
    def tearDownClass(self):
        self.couch_container.stop()

if __name__ == '__main__':
    unittest.main()