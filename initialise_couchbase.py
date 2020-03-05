import requests
import subprocess
import polling
import time
import couchbase.exceptions

from couchbase.cluster import Cluster, PasswordAuthenticator
from nmosregistration.registryaggregatorservice import RegistryAggregatorService
from nmosregistration.config import config


TIMEOUT = 2


def get_registry_config_data():
    buckets = config["registry"].get("buckets")
    if not buckets or any(not buckets[x] for x in buckets):
        raise ValueError("No value for buckets in config")

    username = config["registry"].get("username")
    password = config["registry"].get("password")
    if not username or not password:
        raise ValueError("No username and/or password value in config")

    hosts = config["registry"].get("hosts", '127.0.0.1')
    port = config["registry"].get("port", 8091)

    return hosts[0], port, buckets, username, password


def _initialise_cluster(host, port, bucket, username, password):

    requests.get(
        'http://127.0.0.1:8091/ui/index.html',
    )
    # Initialize node
    requests.post(
        'http://{0}:{1}/nodes/self/controller/settings'.format(host, port),
        auth=('Administrator', 'password'),
        data={
            'path': '/opt/couchbase/var/lib/couchbase/data',
            'index_path': '/opt/couchbase/var/lib/couchbase/data',
            'cbas_path': '/opt/couchbase/var/lib/couchbase/data',
        }
    )
    # Rename node
    requests.post(
        'http://{0}:{1}/node/controller/rename'.format(host, port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'hostname': '127.0.0.1',
        }
    )
    # Setup services
    requests.post(
        'http://{0}:{1}/node/controller/setupServices'.format(host, port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'services': 'kv,index,n1ql,fts',
        }
    )
    # Setup admin username/password
    requests.post(
        'http://{0}:{1}/settings/web'.format(host, port),
        auth=requests.auth.HTTPBasicAuth('Administrator', 'password'),
        data={
            'password': password,
            'username': username,
            'port': port,
        }
    )
    # Build registry bucket
    requests.post(
        'http://{0}:{1}/pools/default/buckets'.format(host, port),
        auth=requests.auth.HTTPBasicAuth(username, password),
        data={
            'flushEnabled': 1,
            'replicaNumber': 0,
            'evictionPolicy': 'valueOnly',
            'ramQuotaMB': 1024,
            'bucketType': 'couchbase',
            'name': bucket['registry'],
        }
    )
    # Build meta bucket
    requests.post(
        'http://{0}:{1}/pools/default/buckets'.format(host, port),
        auth=requests.auth.HTTPBasicAuth(username, password),
        data={
            'flushEnabled': 1,
            'replicaNumber': 0,
            'evictionPolicy': 'valueOnly',
            'ramQuotaMB': 128,
            'bucketType': 'couchbase',
            'name': bucket['meta'],
        }
    )
    # Set indexer mode
    requests.post(
        'http://{0}:{1}/settings/indexes'.format(host, port),
        auth=requests.auth.HTTPBasicAuth(username, password),
        data={
            'indexerThreads': 0,
            'maxRollbackPoints': 5,
            'memorySnapshotInterval': 200,
            'storageMode': 'forestdb',
        }
    )


host, port, bucket_config, username, password = get_registry_config_data()

# Run Docker Compose to bring up Couchbase Server (non-blocking)
subprocess.run(["docker-compose -f ./tests/docker-compose.yml up -d"], check=True, shell=True)

# Poll for server coming up
polling.poll(
    lambda: requests.get("http://{}:{}".format(host, port)).status_code == 200,
    step=TIMEOUT,
    timeout=TIMEOUT * 10,
    ignore_exceptions=(requests.exceptions.ConnectionError)
)

# Initialise Cluster
_initialise_cluster(host, port, bucket_config, username, password)
print("Couchbase cluster is up and configured on Host: {} and Port: {}".format(host, 1908))

time.sleep(10)

# Bring up Registry API
registry = RegistryAggregatorService()
print("Registry API Service available on host: {} and port: {}".format(host, 5328))

# Setup Indexes for databases
cluster = Cluster('couchbase://{}'.format(host))
auth = PasswordAuthenticator(username, password)
cluster.authenticate(auth)
test_bucket = cluster.open_bucket(bucket_config['registry'])
test_bucket_manager = test_bucket.bucket_manager()
test_meta_bucket = cluster.open_bucket(bucket_config['meta'])
test_meta_bucket_manager = test_bucket.bucket_manager()

try:
    test_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)
    test_meta_bucket_manager.n1ql_index_create('test-bucket-primary-index', primary=True)
except couchbase.exceptions.KeyExistsError:
    pass

time.sleep(5)
registry.run()

try:
    print("Stopping API Service")
    registry.stop()
    print("Killing Container")
    subprocess.run(["docker kill $(docker ps -q)"], check=True, shell=True)
except Exception as e:
    print(e)
