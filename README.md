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

