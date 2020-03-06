# NMOS Registry Registration API Service

Provides a service implementing the NMOS Registration API, specified in AMWA IS-04.

The API will present itself at [http://localhost:8235/x-nmos/registration/].

## Installing with Python

Before installing this library please make sure you have installed the [NMOS Common Library](https://github.com/bbc/nmos-common), on which this API depends.

The registration API also requires a datastore. Either [etcd](https://github.com/coreos/etcd) or [Couchbase Server](https://www.couchbase.com) to be installed.

The legacy etcd store can be installed on debain distributions using apt:

```
sudo apt-get install etcd

```

The modern Couchbase datastore [requires some further steps](https://docs.couchbase.com/python-sdk/2.5/start-using-sdk.html). The Python package depends on the C `libcouchbase` SDK, installed on debian distributions as follows:

```
# Only needed during first-time setup:
wget http://packages.couchbase.com/releases/couchbase-release/couchbase-release-1.0-6-amd64.deb
sudo dpkg -i couchbase-release-1.0-6-amd64.deb
# Will install or upgrade packages
sudo apt-get update
sudo apt-get install libcouchbase-dev libcouchbase2-bin build-essential
```

In addition `libsystemd-dev` is required to  be installed for `cysystemd`:

```
sudo apt install libsystemd-dev
```

Once all dependencies are satisfied run the following commands to install the API:

```
pip install setuptools
sudo python setup.py install
```

## Configuration

The Registration API makes use of two configuration files. The first is native to the Registration API and is described below. The second forms part of the [NMOS Common Library](https://github.com/bbc/nmos-common) and is described in that repository. Note that you will likely have to configure items in both files.

The native Registration API configuration should consist of a JSON object in the file `/etc/ips-regaggregator/config.json`. The following attributes may be set within the object:

*   **priority:** \[integer\] Sets a priority value for this Registration API instance between 0 and 255. A value of 100+ indicates a development rather than production instance. Default: 100.
*   **https_mode:** \[string\] Switches the API between HTTP and HTTPS operation. "disabled" indicates HTTP mode is in use, "enabled" indicates HTTPS mode is in use. Default: "disabled".
*   **enable_mdns:** \[boolean\] Provides a mechanism to disable mDNS announcements in an environment where unicast DNS is preferred. Default: true.
*   **oauth_mode:** \[boolean\] Switches the API between being secured using OAuth2 and not using authorization. Default: false.

An example configuration file is shown below:

```json
{
  "priority": "30",
  "https_mode": "enabled",
  "enable_mdns": false,
  "oauth_mode": true
}
```

## Running the Registration API

### Non-blocking

Run the following script to start the Registration API in a non-blocking manner, and then stop it again at a later point:

```Python
    from nmosregistration.registryaggregatorservice import RegistryAggregatorService

    service = RegistryAggregatorService()
    service.start()

    # Do something else until ready to stop

    service.stop()
```

### Blocking

It is also possible to run Registration API in a blocking manner:

```python
from nmosregistration.registryaggregatorservice import RegistryAggregatorService

service = RegistryAggregatorService()
service.run() # Runs forever
```

### Local Development Datastore

To run a local instance of Couchbase Server, the easiest approach is to run `docker-compose` in the `tests/` directory and run a test container. Some setup is required, either through a web GUI accessible via `http://[host]:8091` or POSTing the http requests specified in `_initialise_cluster()` within `test_couchbase` in `tests/v1_0/`.

For a full development environment, a `Vagrantfile` is provided in the root of the directory that provisions a Virtual Machine with all the required dependencies. This can be run using:

```bash
vagrant up --provision
```

Note this will require both Vagrant and Ansible to be installed in order to provision the VM. Once the machine has been provisioned, running the following script will configure a single node cluster and bring up the API Service:

```bash
vagrant ssh  # ssh into the VM
python3 initialise_couchbase.py  # initialise cluster
```

## Tests

Unit tests are provided.  Currently these have hard-coded dummy/example hostnames, IP addresses and UUIDs.  You will need to edit the Python files in the test/ directories to suit your needs and then "make test".

## Debian Packaging

Debian packaging files are provided for internal BBC R&D use.
These packages depend on packages only available from BBC R&D internal mirrors, and will not build in other environments. For use outside the BBC please use python installation method.
