# NMOS Registration API Implementation Changelog

## 0.8.1
- Replace RequiresAuth decorator with AuthMiddleware middleware

## 0.8.0
- Use official etcd ports

## 0.7.11
- Alter executable to run using Python3, alter `stdeb` to replace python 2 package

## 0.7.10
- Clean-up before stopping service thread

## 0.7.9
- Add `api_auth` text record to multicast announcements

## 0.7.8
- Update schemas for v1.3 and earlier changes

## 0.7.7
- Import config from seperate file, add OAUTH_MODE config parameter

## 0.7.6
- Add cleanup function when stopping service

## 0.7.5
- Fix python3 errors

## 0.7.4
- Move NMOS packages from recommends to depends

## 0.7.3
- Add systemd ready notification when service has started

## 0.7.2
- Add Python3 linting stage to CI, fix linting

## 0.7.1
- Fix missing files in Python 3 Debian package

## 0.7.0
- Addition of OAuth2 security decorators and added linting stage to Jenkins CI

## 0.6.6
- Made to work with python 3

## 0.6.5
- Add missing dependency

## 0.6.4
- Fix bug causing format validation to be skipped

## 0.6.3
- Fix bug preventing use of priorities 1 through 99

## 0.6.2
- Update mDNS behaviour based on latest v1.3 draft

## 0.6.1
- Update schemas for v1.3

## 0.6.0
- Add support for new mDNS service type in v1.3

## 0.5.0
- Add config option to enable/disable mDNS announcement

## 0.4.0
- Disable v1.0 API when running in HTTPS mode

## 0.3.0
- Add provisional support for IS-04 v1.3
