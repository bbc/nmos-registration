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

# Set global timeout
class MyTimeout(TimeoutSauce):
    def __init__(self, *args, **kwargs):
        connect = kwargs.get('connect', 0.5)
        read = kwargs.get('read', connect)
        super(MyTimeout, self).__init__(connect=connect, read=read)

requests.adapters.TimeoutSauce = MyTimeout

class CouchbaseInterface(object):
    def __init__(self, cluster_address, bucket, *args, **kwargs):
        self.cluster = couchbase.cluster.Cluster(cluster_address)
        self.registry = cluster.open_bucket(bucket)
        self.bucket = bucket

    def insert(self, rtype, rkey, value, ttl=12):
        self.registry.insert(rkey, value, ttl=ttl) # TODO: Check for key conflict/break when fail due to
        write_time = time.time_ns()
        self.registry.mutate_in(rkey, couchbase.subdocument.upsert('last_updated', write_time, xattr=True))
        self.registry.mutate_in(rkey, couchbase.subdocument.upsert('created_at', write_time, xattr=True))
        self.registry.mutate_in(rkey, couchbase.subdocument.upsert('resource_type', rtype, xattr=True))
        self.registry.mutate_in(rkey, couchbase.subdocument.upsert('node_id', 'hmmst', xattr=True)) # TODO: How?

    # Legacy put command warps around insert
    def put(self, rtype, rkey, value, ttl=12):
        self.insert(rtype, rkey, value, ttl)

    def remove(self, rkey):
        self.registry.remove(rkey)

    # Legacy delete command wraps around remove
    def delete(self, rtype, rkey):
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
    