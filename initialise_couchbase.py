import requests
import subprocess
import polling

from nmosregistration.registryaggregatorservice import RegistryAggregatorService

BUCKET_CONFIG = {
    'registry': 'nmos-test',
    'meta': 'nmos-meta-config'
}
USERNAME = 'nmos-test'
PASSWORD = 'password'

HOST = '127.0.0.1'
PORT = 8091

TIMEOUT = 2


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
            'password': PASSWORD,
            'username': USERNAME,
            'port': port,
        }
    )
    # Build registry bucket
    requests.post(
        'http://{0}:{1}/pools/default/buckets'.format(host, port),
        auth=requests.auth.HTTPBasicAuth(USERNAME, PASSWORD),
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
        auth=requests.auth.HTTPBasicAuth(USERNAME, PASSWORD),
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
        auth=requests.auth.HTTPBasicAuth(USERNAME, password),
        data={
            'indexerThreads': 0,
            'maxRollbackPoints': 5,
            'memorySnapshotInterval': 200,
            'storageMode': 'forestdb',
        }
    )


# Run Docker Compose to bring up Couchbase Server (non-blocking)
subprocess.run(["docker-compose -f ./tests/docker-compose.yml up -d"], check=True, shell=True)

# Poll for server coming up
polling.poll(
    lambda: requests.get("http://{}:{}".format(HOST, PORT)).status_code == 200,
    step=TIMEOUT,
    poll_forever=True,
    ignore_exceptions=(requests.exceptions.ConnectionError)
)

# Initialise Cluster
_initialise_cluster(HOST, PORT, BUCKET_CONFIG, USERNAME, PASSWORD)
print("Couchbase cluster is up and configured on Host: {} and Port: {}".format(HOST, PORT))

# Bring up API
registry = RegistryAggregatorService()
registry.run()
