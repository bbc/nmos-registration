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
from requests import Response
import json
import gevent
from six.moves.urllib.parse import urlencode
import couchbase.exceptions
import couchbase.subdocument as subdoc
from couchbase.cluster import Cluster, PasswordAuthenticator
import time
from nmoscommon.timestamp import Timestamp
import string
from flask import make_response

legacy_key_table = {
    '@_apiversion': 'api_version'
}

def _legacy_key_lookup(key):
    try:
        return legacy_key_table[key]
    except KeyError:
        # TODO: More proper handling of any additional keys starting '@_'?
        #       - May just be sufficient to keep table and return otherwise, need to see other cases.
        return key

class CouchbaseInterface(object):
    type = 'couchbase'
    def __init__(self, cluster_address, username, password, bucket, *args, **kwargs):
        self.cluster = Cluster('couchbase://{}'.format(','.join(cluster_address)))
        auth = PasswordAuthenticator(username, password)
        self.cluster.authenticate(auth)
        self.registry = self.cluster.open_bucket(bucket)
        self.bucket = bucket

    class RegistryUnavailable(Exception):
        pass

    def _get_associated_node_id(self, rtype, value):
        if rtype == 'node':
            return value['id']
        elif rtype == 'device':
            return value['node_id']
        elif rtype in ['receiver', 'sender', 'source', 'flow']:
            try:
                return self.registry.get(value['device_id']).value['node_id']
            except KeyError:
                return self.registry.get(self.registry.get(value['source_id']).value['device_id']).value['node_id']

    def get_health(self, rkey, port=None):
        return self.registry.lookup_in(
            rkey, subdoc.get('$document.exptime', xattr=True)
        )['$document.exptime']

    def upsert(self, rtype, rkey, value, xattrs, ttl=12):
        try:
            upsert_result = self.registry.upsert(rkey, value, ttl=ttl)
            r = make_response(json.dumps(value), 200)
        except couchbase.exceptions.KeyExistsError:
            return make_response(409)
        if upsert_result.success:
            write_time = Timestamp.get_time().to_nanosec()
            subdoc_results = []

            xattrs['last_updated'] = write_time
            xattrs['created_at'] = write_time
            xattrs['resource_type'] = rtype
            xattrs['node_id'] = self._get_associated_node_id(rtype, value)

            # Store any additional extended attributes
            for key, value in xattrs.items():
                subdoc_results.append(self.registry.mutate_in(
                    rkey,
                    subdoc.upsert(_legacy_key_lookup(key), value, xattr=True)
                ))

            failed_subdoc_ops = [result for result in subdoc_results if result.success == False]
            if len(failed_subdoc_ops) > 0:
                return failed_subdoc_ops

        if rtype != 'node':
            ttl = self.get_health(xattrs['node_id'])

        try:
            touch_result = self.registry.touch(rkey, ttl=ttl)
        except Exception:
            self.remove(rkey)
            r = make_response(500)

        return r

    # Legacy put command warps around upsert. Sanitises inputs, removing etcd specific decoration.
    def put(self, rtype, rkey, value, ttl=12, port=None):
        try:
            if rtype[0:-1] != self.registry.lookup_in(
                rkey,
                subdoc.get('resource_type', xattr=True)
            )['resource_type']:
                return make_response('Key already exists', 409)
        except couchbase.exceptions.SubdocPathNotFoundError:
            pass
        except couchbase.exceptions.NotFoundError:
            pass
        # Remove extra-spec fields and add to dict of additional extended attributes
        value = json.loads(value)
        xattr_keys = [key for key in value.keys() if key[0] == '@']
        xattrs = {}
        for key in xattr_keys:
            xattrs[key] = value[key]
            del value[key]

        # rtype[0:-1] naïvely strips the final character
        return self.upsert(rtype[0:-1], rkey, value, xattrs, ttl=ttl)

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
    
    def get_descendents(self, rtype, rkey):
        if rtype == 'node':
            query = couchbase.n1ql.N1QLQuery(
                "SELECT id from `{0}` WHERE meta().xattrs.node_id = '{1}'"
                .format(self.bucket, rkey)
            )
        else:
            query = couchbase.n1ql.N1QLQuery(
                "SELECT id FROM `{0}` WHERE `{1}_id` = '{2}'"
                .format(self.bucket, rtype, rkey)
            )

        descendents = []
        try:
            for descendent in self.registry.n1ql_query(query):
                descendents.append(descendent['id'])
        except couchbase.n1ql.N1QLError:
            return []
        return descendents
    
    # TODO: Strip useless legacy resource_type nonsense? Validate returned doc is correct type??
    def get(self, resource_type, rkey, port=None):
        return self.registry.get(rkey).value

    def resource_exists(self, resource_type, rkey):
        try:
            self.get(resource_type, rkey)
            actual_type = self.registry.lookup_in(rkey, subdoc.get('resource_type', xattr=True))
        except couchbase.exceptions.NotFoundError:
            return False
        return actual_type['resource_type'] == resource_type[0:-1]

    def touch(self, rkey, ttl=12):
        return self.registry.touch(rkey, ttl=ttl)
        

    def put_health(self, rkey, value, ttl=12, port=None):
        for descendent in self.get_descendents('node', rkey):
            self.touch(descendent, ttl=ttl)
        if self.touch(rkey, ttl).success == True:
            return make_response(json.dumps({'health': value}), 200)

    def remove(self, rkey):
        r = Response()
        try:
            self.registry.remove(rkey)
            r.status_code = 204
        except couchbase.exceptions.NotFoundError:
            r.status_code = 404
            r.reason = 'Key does not exist in registry'
        return r

    def delete(self, resource_type, rkey, port=None):
        r = Response()
        descendents = self.get_descendents(resource_type, rkey)

        try:
            for descendent in descendents:
                self.remove(descendent)
            self.remove(rkey)
            r.status_code = 204
        except couchbase.exceptions.NotFoundError:
            r.status_code = 404
            r.reason = '{} not found in {} bucket'.format(rkey, self.bucket)
        return r
