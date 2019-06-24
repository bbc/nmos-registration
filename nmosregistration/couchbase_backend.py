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

from __future__ import absolute_import

from gevent import monkey
monkey.patch_all()

# following block all suffixed with `# noqa E402` - follow up
import requests
from requests.adapters import TimeoutSauce
import json
import gevent
from six.moves.urllib.parse import urlencode
import couchbase
import time
from nmoscommon.timestamp import Timestamp
import string

legacy_key_table = {
    '@_apiversion': 'api_version'
}

def _strip_punctuation(input):
    return input.translate(str.maketrans('', '', string.punctuation))

def _legacy_key_lookup(key):
    try:
        return legacy_key_table[key]
    except KeyError:
        # TODO: More proper handling of any additional keys starting '@_'?
        #       - May just be sufficient to keep table and return otherwise, need to see other cases.
        return key

class CouchbaseInterface(object):
    def __init__(self, cluster_address, username, password, bucket, *args, **kwargs):
        self.cluster = couchbase.cluster.Cluster('couchbase://{}'.format(','.join(cluster_address)))
        auth = couchbase.cluster.PasswordAuthenticator(username, password)
        self.cluster.authenticate(auth)
        self.registry = self.cluster.open_bucket(bucket)
        self.bucket = bucket

    class RegistryUnavailable(Exception):
        pass

    def _get_associated_node_id(self, rtype, rkey):
        device = self.registry.get(rkey)
        return device.value['node_id']

    def insert(self, rtype, rkey, value, xattrs, ttl=12):
        try:
            insert_result = self.registry.insert(rkey, value, ttl=120)
        except couchbase.exceptions.KeyExistsError:
            print('Insert error: the key ({}) already exists'.format(rkey))
            return # TODO: Handle this better
        if insert_result.success:
            write_time = Timestamp.get_time().to_nanosec()
            time.sleep(1)
            subdoc_results = []

            xattrs['last_updated'] = write_time
            xattrs['created_at'] = write_time
            xattrs['resource_type'] = rtype

            if rtype == 'device':
                xattrs['node_id'] = value['node_id']
            elif rtype in ['receiver', 'sender', 'source', 'flow']:
                xattrs['node_id'] = self._get_associated_node_id(value['device_id'])

            # Store any additional extended attributes
            for key, value in xattrs.items():
                subdoc_results.append(self.registry.mutate_in(
                    rkey,
                    couchbase.subdocument.insert(_legacy_key_lookup(key), value, xattr=True)
                ))

            failed_subdoc_ops = [result for result in subdoc_results if result.success == False]
            if len(failed_subdoc_ops) > 0:
                return failed_subdoc_ops

        return {'result': insert_result, 'value': value}

    # Legacy put command warps around insert. Sanitises inputs, removing etcd specific decoration.
    def put(self, rtype, rkey, value, ttl=12, port=None):

        # Remove extra-spec fields and add to dict of additional extended attributes
        value = json.loads(value)
        xattr_keys = [key for key in value.keys() if key[0] == '@']
        xattrs = {}
        for key in xattr_keys:
            xattrs[key] = value[key]
            del value[key]

        # rtype[0:-1] naïvely strips the final character
        return self.insert(rtype[0:-1], rkey, value, xattrs, ttl=ttl)

    def remove(self, rkey):
        self.registry.remove(rkey)

    # Legacy delete command wraps around remove
    def delete(self, rtype, rkey, port=None):
        self.remove(rkey)

        

    # Generalise? Contextual query based on rtype?
    def get_node_residents(self, rkey):
        query = couchbase.n1ql.N1QLQuery(
            "SELECT id FROM {0} WHERE meta().xattrs.node_id = '{1}'"
            .format(self.bucket, rkey)
        )
        residents = []
        for resident in registry.n1ql_query(query):
            residents.append(resident['id'])

        return residents
    
    def get_related_descendents(self, rtype, rkey):
        query = couchbase.n1ql.N1QLQuery(
            "SELECT id FROM {0} WHERE `{1}_id` = '{2}'"
            .format(self.bucket, rtype, rkey)
        )

        descendents = []
        for descendent in registry.n1ql_query(query):
            descendents.append(descendent['id'])
        
        return descendents

    def get_descendents(self, rtype, rkey):
        if rtype=='node':
            return self.get_node_residents(rkey)
        elif rtype=='device':
            return get_related_descendents(rtype, rkey)
        elif rtype=='source':
            return get_related_descendents(rtype, rkey)
    
    def get(self, rkey):
        return self.registry.get(rkey)

    def resource_exists(self, resource_type, rkey):
        print('determining resource existence')
        try:
            self.get(rkey)
            actual_type = self.registry.lookup_in(rkey, couchbase.subdocument.get('resource_type', xattr=True))
        except couchbase.exceptions.NotFoundError:
            return False
        return actual_type['resource_type'] == resource_type[0:-1]
