%global module_name registryaggregator

Name:           python-%{module_name}
Version:        0.8.0
Release:        1%{?dist}
License:        Internal Licence
Summary:        Provides the ipstudio registry aggregator service, interfacing with etcd

Source0:        %{module_name}-%{version}.tar.gz
Source1:        ips-api-registration.conf
Source2:        ips-regaggregator.service

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-flask              >= 0.10.2
BuildRequires:  python-jsonschema
BuildRequires:  systemd

Requires:       python
Requires:       python-flask              >= 0.10.2
Requires:       python-requests           >= 0.9.3
Requires:       python-ws4py
Requires:       ips-etcd
Requires:       ips-reverseproxy-common
Requires:       python-jsonschema
%{?systemd_requires}

%description
Implementation of the registration interface

%prep
%setup -n %{module_name}-%{version}

%build
%{py2_build}

%install
%{py2_install}

# Install config file
install -d -m 0755 %{buildroot}%{_sysconfdir}/ips-regaggregator
install -D -p -m 0644 etc/ips-regaggregator/config.json %{buildroot}%{_sysconfdir}/ips-regaggregator/config.json

# Install systemd unit file
install -D -p -m 0644 %{SOURCE2} %{buildroot}%{_unitdir}/ips-regaggregator.service

# Install Apache config file
install -D -p -m 0644 %{SOURCE1} %{buildroot}%{_sysconfdir}/httpd/conf.d/ips-apis/ips-api-nmosaggregator.conf

%pre
getent group ipstudio >/dev/null || groupadd -r ipstudio
getent passwd ipstudio >/dev/null || \
    useradd -r -g ipstudio -d /dev/null -s /sbin/nologin \
        -c "IP Studio user" ipstudio

%post
mkdir -p /run/ips-regaggregator
mkdir -p /etc/ips-regaggregator
chown -R ipstudio:ipstudio /run/ips-regaggregator
chown -R ipstudio:ipstudio /etc/ips-regaggregator
mkdir -p /var/log/ips-regaggregator
chown -R ipstudio:ipstudio /var/log/ips-regaggregator
chmod -R g+w /var/log/ips-regaggregator
%systemd_post ips-regaggregator.service
systemctl reload httpd
systemctl start ips-regaggregator

%preun
systemctl stop ips-regaggregator

%clean
rm -rf %{buildroot}

%files
%{_bindir}/nmosregistration

%{_unitdir}/%{name}.service

%{python2_sitelib}/%{module_name}
%{python2_sitelib}/%{module_name}-%{version}*.egg-info

%defattr(-,ipstudio, ipstudio,-)
%config(noreplace) %{_sysconfdir}/ips-regaggregator/config.json

%config %{_sysconfdir}/httpd/conf.d/ips-apis/ips-api-nmosaggregator.conf

%changelog
* Tue Apr 25 2017 Sam Nicholson <sam.nicholson@bbc.co.uk> - 0.1.0-1
- Initial packaging for RPM
