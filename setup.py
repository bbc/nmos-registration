#!/usr/bin/python
#
# Copyright 2017 British Broadcasting Corporation
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


from setuptools import setup
from distutils.version import LooseVersion
import os
import sys

def check_packages(packages):
    failure = False
    for python_package, package_details in packages:
        try:
            __import__(python_package)
        except ImportError as err:
            failure = True
            print "Cannot find", python_package,
            print "you need to install :", package_details

    return not failure

def check_dependencies(packages):
    failure = False
    for python_package, dependency_filename, dependency_url in packages:
        try:
            __import__(python_package)
        except ImportError as err:
            failure = True
            print
            print "Cannot find", python_package,
            print "you need to install :", dependency_filename
            print "... originally retrieved from", dependency_url

    return not failure

def is_package(path):
    return (
        os.path.isdir(path) and
        os.path.isfile(os.path.join(path, '__init__.py'))
        )

def find_packages(path, base="" ):
    """ Find all packages in path """
    packages = {}
    for item in os.listdir(path):
        dir = os.path.join(path, item)
        if is_package( dir ):
            if base:
                module_name = "%(base)s.%(item)s" % vars()
            else:
                module_name = item
            packages[module_name] = dir
            packages.update(find_packages(dir, module_name))
    return packages

packages = find_packages(".")
package_names = packages.keys()

packages_required = [
]

deps_required = []

setup(name = "nmosregistration",
      version = "0.1.0",
      description = "nmos registration API",
      url='www.nmos.tv',
      author='Peter Brightell',
      author_email='peter.brightwell@bbc.co.uk',
      license='Apache 2',
      packages = package_names,
      package_dir = packages,
      install_requires = packages_required,
      scripts = [
                ],
      data_files=[
          ('/usr/bin', ['bin/nmosregistration'])
      ],
      long_description = """
Provides a service implementing the NMOS Registration API

"""
      )
