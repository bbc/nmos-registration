import requests
import subprocess
import polling
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
print("Couchbase cluster is up and configured on Host: {} and Port: {}".format(host, port))
