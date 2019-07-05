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

AGGREGATOR_PORT = 8236

API_VERSION = 'v1.0'

def _initialise_cluster(host, port, bucket, username, password):
    # Initialize node
    requests.post('http://{0}:{1}/nodes/self/controller/settings'.format(host,port),
        auth=('Administrator', 'password'),
        data={
            'path': '/opt/couchbase/var/lib/couchbase/data',
            'index_path': '/opt/couchbase/var/lib/couchbase/data',
            'cbas_path': '/opt/couchbase/var/lib/couchbase/data',
        }
    )
    # Rename node
    requests.post('http://{0}:{1}/node/controller/rename'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'hostname': '127.0.0.1',
        }
    )
    # Setup services
    requests.post('http://{0}:{1}/node/controller/setupServices'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'services': 'kv,index,n1ql,fts',
        }
    )
    # Setup admin username/password
    requests.post('http://{0}:{1}/settings/web'.format(host,port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'password': TEST_PASSWORD,
            'username': TEST_USERNAME,
            'port': port,
        }
    )
    # Build bucket
    requests.post('http://{0}:{1}/pools/default/buckets'.format(host,port),
        auth=requests.auth.HTTPBasicAuth(TEST_USERNAME, TEST_PASSWORD),
        data={
            'flushEnabled': 1,
            'replicaNumber': 0,
            'evictionPolicy': 'valueOnly',
            'ramQuotaMB': 2048,
            'bucketType': 'couchbase',
            'name': BUCKET_NAME,
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

def _put_doc(bucket, key, value, xattrs, fill_timestamp_xattrs=True, ttl=12):
    bucket.insert(key, value, ttl=ttl)
    time.sleep(1)
    _put_xattrs(bucket, key, xattrs, fill_timestamp_xattrs)
    bucket.touch(key, ttl=ttl)

def _get_xattrs(bucket, key, xattrs):
    results = {}
    for xkey in xattrs:
        try:
            results[xkey] = bucket.lookup_in(key, subdoc.get(xkey, xattr=True))['{}'.format(xkey)]
        except couchbase.exceptions.SubdocPathNotFoundError:
            results[xkey] = None
    return results

class TestCouchbase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.couch_container = DockerCompose('{}/tests/'.format(os.getcwd()))
        self.couch_container.start()
        self.couch_container.wait_for('http://localhost:8091')

        host = self.couch_container.get_service_host('couchbase', 8091)
        port = self.couch_container.get_service_port('couchbase', 8091)
        
        _initialise_cluster(host, port, BUCKET_NAME, TEST_USERNAME, TEST_PASSWORD)
        
        time.sleep(10) # TODO, properly wait for setup somehow, possible long poll?

        self.registry = RegistryAggregatorService()
        self.registry.config['registry'] = {
            "type": "couchbase",
            "hosts": [host],
            "port": port,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "bucket": BUCKET_NAME
        }
        self.registry.config['priority'] = 169
        self.registry.service_port = AGGREGATOR_PORT
        self.registry.start()

        cluster = Cluster('couchbase://{}'.format(host))
        auth = PasswordAuthenticator(TEST_USERNAME, TEST_PASSWORD)
        cluster.authenticate(auth)
        self.test_bucket = cluster.open_bucket(BUCKET_NAME)
        self.test_bucket_manager = self.test_bucket.bucket_manager()

        try:
            self.test_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)
        except couchbase.exceptions.KeyExistsError:
            pass

    def test_document_write(self):
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )
        self.assertDictEqual(self.test_bucket.get(doc_body['id']).value, doc_body)
   
    def test_register_response(self):
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        self.assertEqual(aggregator_response.status_code, 200)
        self.assertEqual(aggregator_response.headers['location'], '/x-nmos/registration/{}/resource/nodes/{}/'.format(API_VERSION, doc_body['id']))
        self.assertDictEqual(aggregator_response.json(), doc_body)

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
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        xattrs = _get_xattrs(
            self.test_bucket,
            doc_body['id'],
            ['last_updated', 'created_at', 'resource_type', 'api_version']
        )
        lookup_time = Timestamp.get_time().to_nanosec()

        self.assertEqual(xattrs['api_version'], API_VERSION)
        self.assertEqual(xattrs['resource_type'], 'node')
        self.assertEqual(xattrs['created_at'], xattrs['last_updated'])
        self.assertLessEqual(xattrs['created_at'], lookup_time)
        self.assertGreaterEqual(xattrs['created_at'], post_time)

    def test_resource_update(self):
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})

        test_node['href'] = 'https://www.youtube.com/watch?v=taUqt_E0aOs'
        request_payload = {
            'type': 'node',
            'data': test_node
        }
        
        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)

    def test_duplicate_insert(self):
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})

        test_device = doc_generator.generate_device()
        test_device['id'] = test_node['id']
        test_device['node_id'] = test_node['id']
        request_payload = {
            'type': 'device',
            'data': test_device
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        self.assertEqual(aggregator_response.status_code, 409)
        self.assertDictEqual(self.test_bucket.get(test_device['id']).value, test_node)

    def test_node_expiry(self):
        """Ensure nodes expire 12s after registration if no further heartbeats are received"""
        doc_body = util.json_fixture("fixtures/node.json")
        request_payload = {
            'type': 'node',
            'data': doc_body
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        time.sleep(13)

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(doc_body['id'])

    def test_device_expiry_with_node(self):
        """Ensure devices expire at the same time as parent nodes after registration if no further heartbeats are received"""
        test_device = doc_generator.generate_device()
        test_node = doc_generator.generate_node()
        test_node['id'] = test_device['node_id']

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'}, ttl=12)


        request_payload = {
            'type': 'device',
            'data': test_device
        }

        time.sleep(2)

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        node_ttl = _get_xattrs(self.test_bucket, test_node['id'], ['$document.exptime'])['$document.exptime']
        device_ttl = _get_xattrs(self.test_bucket, test_device['id'], ['$document.exptime'])['$document.exptime']

        self.assertEqual(node_ttl, device_ttl)

        time.sleep(11)

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_device['id'])
        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_node['id'])

    def test_get_resource(self):
        """Ensure GET requests return proper resource information"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node', 'api_version': 'v1.2'})
        time.sleep(1)
        
        aggregator_response = requests.get(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource/node/{}'.format(AGGREGATOR_PORT, API_VERSION, test_node['id'])
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
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
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
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
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
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        self.assertEqual(
            _get_xattrs(self.test_bucket, test_source['id'], ['node_id'])['node_id'],
            test_node['id'] # source
        )

    def test_register_flow_with_node_xattr(self):
        """Ensure that when a source is registered, the document is stored with the
           correct extended attributes associating it with a parent node"""
        test_device = doc_generator.generate_device()
        test_source = doc_generator.generate_source()
        test_flow = doc_generator.generate_flow()
        del test_flow['device_id']
        test_flow['source_id'] = test_source['id']
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
        _put_doc(
            self.test_bucket,
            test_source['id'],
            test_source,
            {'resource_type': 'source', 'node_id': test_device['node_id']}
        )

        request_payload = {
            'type': 'flow',
            'data': test_flow
        }

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource'.format(AGGREGATOR_PORT, API_VERSION),
            json=request_payload
        )

        self.assertEqual(
            _get_xattrs(self.test_bucket, test_flow['id'], ['node_id'])['node_id'],
            test_node['id'] # source
        )

    def test_delete_node_solo(self):
        """Ensure a DELETE request deregisters an isolated node"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})
        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)

        aggregator_response = requests.delete(
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource/node/{}'.format(
                AGGREGATOR_PORT,
                API_VERSION,
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
            'http://0.0.0.0:{}/x-nmos/registration/{}/resource/node/{}'.format(
                AGGREGATOR_PORT,
                API_VERSION,
                test_node['id']
            )
        )

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_node['id'])

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_device['id'])

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_source['id'])

    def test_health_response(self):
        """Ensure a POST to the health route returns the correct response body and status code"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'})

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/health/nodes/{}'.format(
                AGGREGATOR_PORT,
                API_VERSION,
                test_node['id']
            )
        )

        self.assertEqual(aggregator_response.status_code, 200)
        self.assertEqual(list(aggregator_response.json().keys()), ['health'])
        self.assertAlmostEqual(aggregator_response.json()['health'], time.time(), -2)

    def test_health_expiry(self):
        """Ensure a POST to the health route extends the expiry of the appropriate node"""
        test_node = doc_generator.generate_node()

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'}, ttl=12)

        time.sleep(5)

        prior_ttl = _get_xattrs(self.test_bucket, test_node['id'], ['$document.exptime'])['$document.exptime']

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/health/nodes/{}'.format(
                AGGREGATOR_PORT,
                API_VERSION,
                test_node['id']
            )
        )

        post_ttl = _get_xattrs(self.test_bucket, test_node['id'], ['$document.exptime'])['$document.exptime']

        self.assertGreater(post_ttl, prior_ttl)

        time.sleep(7)

        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)

        time.sleep(6)

        with self.assertRaises(couchbase.exceptions.NotFoundError):
            self.test_bucket.get(test_node['id'])

    def test_health_expiry_chidren(self):
        """Ensure a POST to the health route extends the expiry of the appropriate node and all children"""
        test_device = doc_generator.generate_device()
        test_source = doc_generator.generate_source()
        test_source['device_id'] = test_device['id']
        test_node = doc_generator.generate_node()
        test_node['id'] = test_device['node_id']

        prior_ttl = {}
        post_ttl = {}

        _put_doc(self.test_bucket, test_node['id'], test_node, {'resource_type': 'node'}, ttl=12)
        # Retrieve ttl as unix timestamp such that children are inserted with same ttl as with posting to aggregator
        prior_ttl['node'] = _get_xattrs(self.test_bucket, test_node['id'], ['$document.exptime'])['$document.exptime']


        _put_doc(
            self.test_bucket,
            test_device['id'],
            test_device,
            {'resource_type': 'device', 'node_id': test_node['id']},
            ttl=prior_ttl['node']
        )
        _put_doc(
            self.test_bucket,
            test_source['id'],
            test_source,
            {'resource_type': 'source', 'node_id': test_node['id']},
            ttl=prior_ttl['node']
        )

        time.sleep(5)

        prior_ttl['device'] = _get_xattrs(self.test_bucket, test_device['id'], ['$document.exptime'])['$document.exptime']
        prior_ttl['source'] = _get_xattrs(self.test_bucket, test_source['id'], ['$document.exptime'])['$document.exptime']

        self.assertListEqual(list(prior_ttl.values()), [prior_ttl['node'], prior_ttl['node'], prior_ttl['node']])

        aggregator_response = requests.post(
            'http://0.0.0.0:{}/x-nmos/registration/{}/health/nodes/{}'.format(
                AGGREGATOR_PORT,
                API_VERSION,
                test_node['id']
            )
        )
        

        post_ttl['node'] = _get_xattrs(self.test_bucket, test_node['id'], ['$document.exptime'])['$document.exptime']
        post_ttl['device'] = _get_xattrs(self.test_bucket, test_device['id'], ['$document.exptime'])['$document.exptime']
        post_ttl['source'] = _get_xattrs(self.test_bucket, test_source['id'], ['$document.exptime'])['$document.exptime']

        self.assertListEqual(list(post_ttl.values()), [post_ttl['node'], post_ttl['node'], post_ttl['node']])

        self.assertGreater(post_ttl['node'], prior_ttl['node'])

        time.sleep(7)

        self.assertDictEqual(self.test_bucket.get(test_node['id']).value, test_node)
        self.assertDictEqual(self.test_bucket.get(test_device['id']).value, test_device)
        self.assertDictEqual(self.test_bucket.get(test_source['id']).value, test_source)

        time.sleep(6)

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