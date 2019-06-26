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
import couchbase.subdocument as subdoc
import couchbase.exceptions
import os
import time
from nmoscommon.timestamp import Timestamp
from testcontainers.compose import DockerCompose
from testcontainers.core.container import DockerContainer
from . import util
import tests.helpers.doc_generator as doc_generator

from nmosregistration.registryaggregatorservice import RegistryAggregatorService
from nmosregistration.couchbase_backend import CouchbaseInterface

BUCKET_NAME = 'nmos-test'
TEST_USERNAME = 'nmos-test'
TEST_PASSWORD = 'password'

AGGREGATOR_PORT = 2202

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
            'replicaNumber': 0,
            'evictionPolicy': 'valueOnly',
            'ramQuotaMB': 2048,
            'bucketType': 'couchbase',
            'name': BUCKET_NAME
        }
    )
    # Set indexer mode
    indexer = requests.post('http://{0}:{1}/settings/indexes'.format(host,port),
        auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, password),
        data={
            'indexerThreads': 0,
            'maxRollbackPoints': 5,
            'memorySnapshotInterval': 200,
            'storageMode': 'forestdb',
        }
    )

def _put_xattrs(bucket, key, xattrs, fill_timestamp_xattrs=True):
    if fill_timestamp_xattrs:
        time_now = Timestamp.get_time().to_nanosec()
        xattrs['last_updated'] = time_now
        xattrs['created_at'] = time_now
    for xkey, xvalue in xattrs.items():
        bucket.mutate_in(key, subdoc.insert(xkey, xvalue, xattr=True))

def _put_doc(bucket, key, value, xattrs, fill_timestamp_xattrs=True):
    bucket.insert(key, value, ttl=12)
    time.sleep(1)
    _put_xattrs(bucket, key, xattrs, fill_timestamp_xattrs)

def _get_xattrs(bucket, key, xattrs):
    results = {}
    for xkey in xattrs:
        try:
            results[xkey] = bucket.lookup_in(key, subdoc.get(xkey, xattr=True))['{}'.format(xkey)]
        except couchbase.exceptions.SubdocPathNotFoundError:
            results[xkey] = None
    return results

class TestSubmissionRouting(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.couch_container = DockerCompose('{}/tests/'.format(os.getcwd()))
        self.couch_container.start()
        self.couch_container.wait_for('http://localhost:8091')

        host = self.couch_container.get_service_host('couchbase', 8091)
        port = self.couch_container.get_service_port('couchbase', 8091)
        
        _initialise_cluster(host, port, BUCKET_NAME, TEST_USERNAME, TEST_PASSWORD)
        
        time.sleep(10) # TODO, properly wait for setup somehow, possible long poll?

        self.registry = RegistryAggregatorService(registry={
            "type": "couchbase",
            "hosts": [host],
            "port": port,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "bucket": BUCKET_NAME
        })
        self.registry.start()

        cluster = Cluster('couchbase://{}'.format(host))
        auth = PasswordAuthenticator(TEST_USERNAME, TEST_PASSWORD)
        cluster.authenticate(auth)
        self.test_bucket = cluster.open_bucket(BUCKET_NAME)
        self.test_bucket_manager = self.test_bucket.bucket_manager()

        self.test_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)

    def test_document_write(self):
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource'.format(AGGREGATOR_PORT),
            json=request_payload
        )
        self.assertDictEqual(self.test_bucket.get(doc_body['id']).value, doc_body)

    def test_xattrs_write(self):
        """Ensure correct extended attributes are appended to the document, including a sensible
           time for created_at and last_updated (which should be equal at the point of insertion)"""
        # TODO, make cluster a class variable? Set up in setUpClass and pass around?
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        post_time = Timestamp.get_time().to_nanosec()
        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource'.format(AGGREGATOR_PORT),
            json=request_payload
        )

        last_updated = self.test_bucket.lookup_in(doc_body['id'], subdoc.get('last_updated', xattr=True))
        created_at = self.test_bucket.lookup_in(doc_body['id'], subdoc.get('created_at', xattr=True))
        resource_type = self.test_bucket.lookup_in(doc_body['id'], subdoc.get('resource_type', xattr=True))
        api_version = self.test_bucket.lookup_in(doc_body['id'], subdoc.get('api_version', xattr=True))
        lookup_time = Timestamp.get_time().to_nanosec()

        self.assertEqual(api_version['api_version'], 'v1.2')
        self.assertEqual(resource_type['resource_type'], 'node')
        self.assertEqual(created_at['created_at'], last_updated['last_updated'])
        self.assertLessEqual(created_at['created_at'], lookup_time)
        self.assertGreaterEqual(created_at['created_at'], post_time)

    def test_get_resource(self):
        """Ensure GET requests return proper resource information"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node', 'api_version': 'v1.2'})
        time.sleep(1)
        
        aggregator_response = requests.get(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource/node/{}'.format(AGGREGATOR_PORT, test_node['id'])
        )

        self.assertDictEqual(aggregator_response.json(), test_node)

    def test_register_without_parents(self):
        """Return error if new child resource is missing appropriate parent resource and do not register child"""
        test_device = doc_generator.generate_device()
        request_payload = {
            'type': 'device',
            'data': test_device
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource'.format(AGGREGATOR_PORT),
            json=request_payload
        )
        self.assertEqual(aggregator_response.status_code, 400)
        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_device['id'])

    def  test_register_device_with_node_parent(self):
        """Ensure that device registers correctly, assocating with the proper node via xattrs"""
        test_device = doc_generator.generate_device()
        test_node = doc_generator.generate_node()
        test_node['id'] = test_device['node_id']

        # Ensure node exists in registry
        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})
        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)

        request_payload = {
            'type': 'device',
            'data': test_device
        }
        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource'.format(AGGREGATOR_PORT),
            json=request_payload
        )

        stored_device = self.test_bucket.get(test_device['id'])
        self.assertEqual(stored_device.value, test_device)

        self.assertEqual(
            self.test_bucket.lookup_in(
                test_device['id'],
                subdoc.get('node_id', xattr=True)
            )['node_id'],
            test_node['id']
        )

    def test_register_source_with_node_xattr(self):
        """Ensure that when a source is registered, the document is stored with the
           correct extended attributes associating it with a parent node"""
        test_device = doc_generator.generate_device()
        test_source = doc_generator.generate_source()
        test_source['device_id'] = test_device['id']
        test_node = doc_generator.generate_node()
        test_node['id'] = test_device['node_id']

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})
        _put_doc(
            self.test_bucket,
            test_device['id'],
            test_device,
            {'resource_type': 'device', 'node_id': test_device['node_id']}
        )

        request_payload = {
            'type': 'source',
            'data': test_source
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource'.format(AGGREGATOR_PORT),
            json=request_payload
        )

        self.assertEqual(
            _get_xattrs(self.test_bucket, test_source['id'], ['node_id'])['node_id'],
            test_node['id'] # source
        )

    def test_delete_node_solo(self):
        """Ensure a DELETE request deregisters an isolated node"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})
        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)

        aggregator_response = requests.delete(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource/node/{}'.format(
                AGGREGATOR_PORT,
                test_node['id']
            )
        )

        self.assertEqual(aggregator_response.status_code, 204)
        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_node['id'])

    def test_delete_node_and_children(self):
        """Ensure a DELETE request to a node with child devices deregisters
           all child resources"""
        test_device = doc_generator.generate_device()
        test_source = doc_generator.generate_source()
        test_source['device_id'] = test_device['id']
        test_node = doc_generator.generate_node()
        test_node['id'] = test_device['node_id']

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})
        _put_doc(self.test_bucket, test_device['id'], test_device, {'resource_type': 'node', 'node_id': test_device['node_id']})
        _put_doc(self.test_bucket, test_source['id'], test_source, {'resource_type': 'node', 'node_id': test_device['node_id']})

        aggregator_response = requests.delete(
            'http://0.0.0.0:{}/x-nmos/registration/v1.2/resource/node/{}'.format(
                AGGREGATOR_PORT,
                test_node['id']
            )
        )

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_node['id'])

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_device['id'])

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_source['id'])

    def tearDown(self):
        self.test_bucket.flush()

    @classmethod
    def tearDownClass(self):
        self.couch_container.stop()
        self.registry.stop()

if __name__ == '__main__':
    unittest.main()