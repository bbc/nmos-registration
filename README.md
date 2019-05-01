# NMOS Registry Registration API Service

Provides a service implementing the NMOS Registration API, specified in AMWA IS-04.

The API will present itself at [http://localhost:8235/x-nmos/registration/].

## Installing with Python

Before installing this library please make sure you have installed the [NMOS Common Library](https://github.com/bbc/nmos-common), on which this API depends. The registration API also requires [etcd](https://github.com/coreos/etcd) to be installed. For debain distributions this can be installed using apt:

```
sudo apt-get install etcd

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

An example configuration file is shown below:

```json
{
  "priority": "30",
  "https_mode": "enabled",
  "enable_mdns": false
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

## Tests

Unit tests are provided.  Currently these have hard-coded dummy/example hostnames, IP addresses and UUIDs.  You will need to edit the Python files in the test/ directories to suit your needs and then "make test".

## Debian Packaging

Debian packaging files are provided for internal BBC R&D use.
These packages depend on packages only available from BBC R&D internal mirrors, and will not build in other environments. For use outside the BBC please use python installation method.
