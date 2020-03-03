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

import json  # noqa E402
import couchbase.exceptions  # noqa E402
import couchbase.subdocument as subdoc  # noqa E402

from flask import make_response  # noqa E402
from requests import Response  # noqa E402
from couchbase.cluster import Cluster, PasswordAuthenticator  # noqa E402
from nmoscommon.timestamp import Timestamp  # noqa E402

from .config import config  # noqa E402

legacy_key_table = {
    '@_apiversion': 'api_version'
}

WS_PERIOD = config['ws_period']
TTL = config['resource_expiry']


def _legacy_key_lookup(key):
    try:
        return legacy_key_table[key]
    except KeyError:
        # TODO: More proper handling of any additional keys starting '@_'?
        #       - May just be sufficient to keep table and return otherwise, need to see other cases.
        return key


class CouchbaseInterface(object):
    type = 'couchbase'
    port = None

    def __init__(self, cluster_address, username, password, buckets, *args, **kwargs):
        self.cluster = Cluster('couchbase://{}'.format(','.join(cluster_address)))
        auth = PasswordAuthenticator(username, password)
        self.cluster.authenticate(auth)
        self.buckets = {}
        for label, bucket_name in buckets.items():
            self.buckets[label] = {
                'bucket': self.cluster.open_bucket(bucket_name),
                'name': bucket_name
            }
        self.ws_period = WS_PERIOD

    class RegistryUnavailable(Exception):
        pass

    def _get_associated_node_id(self, rtype, value, bucket=None):
        if bucket is None:
            bucket = self.buckets['registry']
        if rtype == 'node':
            return value['id']
        elif rtype == 'device':
            return value['node_id']
        elif rtype in ['receiver', 'sender', 'source', 'flow']:
            try:
                return bucket['bucket'].get(value['device_id']).value['node_id']
            except KeyError:
                return bucket['bucket'].get(
                    bucket['bucket'].get(
                        value['source_id']).value['device_id']).value['node_id']

    def get_health(self, rkey, bucket=None, port=None):
        if bucket is None:
            bucket = self.buckets['registry']
        return bucket['bucket'].lookup_in(
            rkey, subdoc.get('$document.exptime', xattr=True)
        )['$document.exptime']

    def upsert(self, rtype, rkey, value, xattrs, bucket=None, ttl=TTL):
        if bucket is None:
            bucket = self.buckets['registry']
        try:
            upsert_result = bucket['bucket'].upsert(rkey, value, ttl=ttl)
            r = make_response(json.dumps(value), 200)
        except couchbase.exceptions.KeyExistsError:
            return make_response(409)
        if upsert_result.success:
            write_time = Timestamp.get_time().to_nanosec()
            subdoc_results = []

            actual_xattrs = {}
            actual_xattrs['last_updated'] = write_time
            actual_xattrs['created_at'] = write_time
            actual_xattrs['resource_type'] = rtype
            actual_xattrs['node_id'] = self._get_associated_node_id(rtype, value)

            for key, value in xattrs.items():
                actual_xattrs[key] = value

            # Store extended attributes
            for key, value in actual_xattrs.items():
                subdoc_results.append(bucket['bucket'].mutate_in(
                    rkey,
                    subdoc.upsert(_legacy_key_lookup(key), value, xattr=True)
                ))

            failed_subdoc_ops = [result for result in subdoc_results if result.success is False]
            if len(failed_subdoc_ops) > 0:
                return failed_subdoc_ops

        if rtype != 'node':
            ttl = self.get_health(actual_xattrs['node_id'])

        try:
            touch_result = bucket['bucket'].touch(rkey, ttl=ttl)
            del touch_result
        except Exception:
            self.remove(rkey)
            r = make_response(500)

        return r, actual_xattrs

    # Legacy put command warps around upsert. Sanitises inputs, removing etcd specific decoration.
    def put(self, rtype, rkey, value, bucket=None, ttl=TTL, ws_period=None, port=None):
        if bucket is None:
            bucket = self.buckets['registry']
        if ws_period is None:
            ws_period = self.ws_period

        xattrs = {}

        try:
            if rtype[0:-1] != bucket['bucket'].lookup_in(
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
        for key in xattr_keys:
            xattrs[key] = value[key]
            del value[key]

        # rtype[0:-1] naïvely strips the final character TODO: replace with lookup
        reg_response, xattrs = self.upsert(rtype[0:-1], rkey, value, xattrs, ttl=ttl)
        xattrs['last_updated'] = xattrs['last_updated'] + ttl
        self.upsert(rtype[0:-1], rkey, value, xattrs, ttl=ttl + ws_period, bucket=self.buckets['meta'])
        return reg_response

    # Generalise? Contextual query based on rtype?
    def get_node_residents(self, rkey, bucket=None):
        if bucket is None:
            bucket = self.buckets['registry']
        query = couchbase.n1ql.N1QLQuery(
            "SELECT id FROM {0} WHERE meta().xattrs.node_id = '{1}'"
            .format(bucket['name'], rkey)
        )
        residents = []
        for resident in bucket['bucket'].n1ql_query(query):
            residents.append(resident['id'])

        return residents

    def get_descendents(self, rtype, rkey, bucket=None):
        if bucket is None:
            bucket = self.buckets['registry']
        if rtype == 'node':
            query = couchbase.n1ql.N1QLQuery(
                "SELECT id from `{0}` WHERE meta().xattrs.node_id = '{1}'"
                .format(bucket['name'], rkey)
            )
        else:
            query = couchbase.n1ql.N1QLQuery(
                "SELECT id FROM `{0}` WHERE `{1}_id` = '{2}'"
                .format(bucket['name'], rtype, rkey)
            )

        descendents = []
        try:
            for descendent in bucket['bucket'].n1ql_query(query):
                descendents.append(descendent['id'])
        except couchbase.n1ql.N1QLError:
            return []
        return descendents

    # TODO: Strip useless legacy resource_type nonsense? Validate returned doc is correct type??
    def get(self, resource_type, rkey, bucket=None, port=None):
        if bucket is None:
            bucket = self.buckets['registry']
        return bucket['bucket'].get(rkey).value

    def resource_exists(self, resource_type, rkey, bucket=None):
        if bucket is None:
            bucket = self.buckets['registry']
        try:
            self.get(resource_type, rkey)
            actual_type = bucket['bucket'].lookup_in(rkey, subdoc.get('resource_type', xattr=True))
        except couchbase.exceptions.NotFoundError:
            return False
        return actual_type['resource_type'] == resource_type[0:-1]

    def touch(self, rkey, bucket=None, ttl=TTL):
        if bucket is None:
            bucket = self.buckets['registry']
        return bucket['bucket'].touch(rkey, ttl=ttl)  # FIXME

    def put_health(self, rkey, value, ttl=TTL, port=None):
        for descendent in self.get_descendents('node', rkey):
            self.touch(descendent, ttl=ttl)
        if self.touch(rkey, ttl=ttl).success is True:
            return make_response(json.dumps({'health': value}), 200)

    def remove(self, rkey, bucket=None):
        if bucket is None:
            bucket = self.buckets['registry']
        r = Response()
        try:
            bucket['bucket'].remove(rkey)
            r.status_code = 204
        except couchbase.exceptions.NotFoundError:
            r.status_code = 404
            r.reason = 'Key does not exist in registry'
        return r

    def _delete_meta(self, rkey, ttl, last_updated, bucket):
        bucket['bucket'].mutate_in(
            rkey,
            subdoc.upsert('last_updated', last_updated, xattr=True)
        )
        return bucket['bucket'].touch(rkey, ttl=ttl)

    def delete(self, resource_type, rkey, bucket=None, meta_bucket=None, port=None):
        if bucket is None:
            bucket = self.buckets['registry']
        if meta_bucket is None:
            meta_bucket = self.buckets['meta']
        r = Response()
        descendents = self.get_descendents(resource_type, rkey)

        try:
            for descendent in descendents:
                self.remove(descendent)
                self._delete_meta(descendent, self.ws_period, Timestamp.get_time().to_nanosec(), meta_bucket)
            self.remove(rkey)
            self._delete_meta(rkey, self.ws_period, Timestamp.get_time().to_nanosec(), meta_bucket)
            r.status_code = 204
        except couchbase.exceptions.NotFoundError:
            r.status_code = 404
            r.reason = '{} not found in {} bucket'.format(rkey, bucket['name'])
        return r
