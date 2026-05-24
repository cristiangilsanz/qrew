# Changelog

## [1.6.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.5.0...qrew-api/v1.6.0) (2026-05-24)


### Features

* allow resubmission of rejected KYC documents ([#84](https://github.com/cristiangilsanz/qrew/issues/84)) ([dddfbf2](https://github.com/cristiangilsanz/qrew/commit/dddfbf2329818b5ea23ae6ea498ae1613e9ad979))
* implement account recovery with KYC re-verification and passkey re-enrollment ([#87](https://github.com/cristiangilsanz/qrew/issues/87)) ([1438a52](https://github.com/cristiangilsanz/qrew/commit/1438a52aa008fec81c860eabfac642a0b90addf2))
* implement cryptographic device binding ([#89](https://github.com/cristiangilsanz/qrew/issues/89)) ([9ba2ce8](https://github.com/cristiangilsanz/qrew/commit/9ba2ce81d40d97346b467989b38b6ed8b30a31d1))
* implement device fingerprint reporting and cross-account detection ([#85](https://github.com/cristiangilsanz/qrew/issues/85)) ([1e4a96e](https://github.com/cristiangilsanz/qrew/commit/1e4a96ec1899eb024bd697f12a4976388cf3da77))
* implement device list and lost-device deregistration ([#90](https://github.com/cristiangilsanz/qrew/issues/90)) ([fafd06e](https://github.com/cristiangilsanz/qrew/commit/fafd06e749e3d2c56c96456075be91b670aae34c))
* implement GET /me, GET /onboarding-status, GET /admin/users ([#95](https://github.com/cristiangilsanz/qrew/issues/95)) ([b3c1fd0](https://github.com/cristiangilsanz/qrew/commit/b3c1fd0d7e3b3fa58dc83530342264077285e343))
* implement KYC-lite OCR with unique national ID constraint ([#86](https://github.com/cristiangilsanz/qrew/issues/86)) ([5f74f0b](https://github.com/cristiangilsanz/qrew/commit/5f74f0bb400219ed71f0a1a631582bb34a1ec08b))
* implement login anomaly detection (impossible travel + concurrent device) ([#88](https://github.com/cristiangilsanz/qrew/issues/88)) ([28f0192](https://github.com/cristiangilsanz/qrew/commit/28f0192ead580ba33e037093b8778239510804ca))
* implement phone number change with re-verification ([#82](https://github.com/cristiangilsanz/qrew/issues/82)) ([a61a4b5](https://github.com/cristiangilsanz/qrew/commit/a61a4b5f4672bfd50ea622c5bb561e26b7264e3b))

## [1.5.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.4.0...qrew-api/v1.5.0) (2026-05-24)


### Features

* implement email change with re-verification ([#81](https://github.com/cristiangilsanz/qrew/issues/81)) ([a36536b](https://github.com/cristiangilsanz/qrew/commit/a36536b147f415f4eaa5dc0cb3919ffb4c0270e7))
* implement passkey list, delete, and rename endpoints ([#78](https://github.com/cristiangilsanz/qrew/issues/78)) ([e1a4b3d](https://github.com/cristiangilsanz/qrew/commit/e1a4b3dec62e1d46efcec273af8288ccc2f57c9e))
* implement password change endpoint for authenticated users ([#80](https://github.com/cristiangilsanz/qrew/issues/80)) ([b4c0cfb](https://github.com/cristiangilsanz/qrew/commit/b4c0cfbf438ee5736a08dc578ad6bb1582abdc78))

## [1.4.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.3.0...qrew-api/v1.4.0) (2026-05-24)


### Features

* implement append-only audit event log with Merkle hash chain ([#74](https://github.com/cristiangilsanz/qrew/issues/74)) ([0af4b98](https://github.com/cristiangilsanz/qrew/commit/0af4b987dec94bf09ea05e1126f5c73f0060c68c))
* implement refresh token rotation with theft detection ([#76](https://github.com/cristiangilsanz/qrew/issues/76)) ([7915116](https://github.com/cristiangilsanz/qrew/commit/7915116fc097237a4e991cb3d382b82725d5c1f5))
* implement session management endpoints ([#77](https://github.com/cristiangilsanz/qrew/issues/77)) ([ac881cb](https://github.com/cristiangilsanz/qrew/commit/ac881cb072a485c31e2df0aef8e507bbf859de3e))

## [1.3.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.2.0...qrew-api/v1.3.0) (2026-05-17)


### Features

* implement KYC review admin endpoint ([#54](https://github.com/cristiangilsanz/qrew/issues/54)) ([aa85f0d](https://github.com/cristiangilsanz/qrew/commit/aa85f0d148ec39fdfbdec51c1eea97ada895c39b))
* implement logout and refresh token revocation ([#55](https://github.com/cristiangilsanz/qrew/issues/55)) ([2f4df8b](https://github.com/cristiangilsanz/qrew/commit/2f4df8b859926c1dc1426fbdb303964e2085f5a9))
* implement passkey authentication endpoints ([#53](https://github.com/cristiangilsanz/qrew/issues/53)) ([cddd719](https://github.com/cristiangilsanz/qrew/commit/cddd7199b92bfd5aa66803afd165ec866a5e9216))
* implement two-tier token login flow and complete-setup endpoint ([#51](https://github.com/cristiangilsanz/qrew/issues/51)) ([889dd53](https://github.com/cristiangilsanz/qrew/commit/889dd53f757d362ff822ed3bd0b9ef99aff7de35))

## [1.2.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.1.0...qrew-api/v1.2.0) (2026-05-17)


### Features

* implement auth refresh endpoint ([#43](https://github.com/cristiangilsanz/qrew/issues/43)) ([ffcf5dc](https://github.com/cristiangilsanz/qrew/commit/ffcf5dcb35757dc4a5e447cd3cd2cfcdf6f20f35))
* implement post-login verification endpoints ([#46](https://github.com/cristiangilsanz/qrew/issues/46)) ([c6c7dde](https://github.com/cristiangilsanz/qrew/commit/c6c7dde7052707cd8ec7bdbe2528bdf8981fc289))
* implement resend verification endpoints ([#45](https://github.com/cristiangilsanz/qrew/issues/45)) ([e19f297](https://github.com/cristiangilsanz/qrew/commit/e19f2979a6c4ea50319fef675852c05140891c0c))

## [1.1.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v1.0.0...qrew-api/v1.1.0) (2026-04-12)


### Features

* implement auth login endpoint ([#34](https://github.com/cristiangilsanz/qrew/issues/34)) ([b5851ad](https://github.com/cristiangilsanz/qrew/commit/b5851ad3e32cf94b1d5c23d564c6e9371b5c5aa8))

## [1.0.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v0.2.0...qrew-api/v1.0.0) (2026-04-10)


### Features

* implement auth register endpoint ([#30](https://github.com/cristiangilsanz/qrew/issues/30)) ([38185d6](https://github.com/cristiangilsanz/qrew/commit/38185d6630365dd640b21c5e40e2ed46b694f1b4))

## [0.2.0](https://github.com/cristiangilsanz/qrew/compare/qrew-api/v0.1.0...qrew-api/v0.2.0) (2026-03-29)


### Features

* scaffold minimal fast api project ([#18](https://github.com/cristiangilsanz/qrew/issues/18)) ([5fe1df5](https://github.com/cristiangilsanz/qrew/commit/5fe1df5b49012ebfdda2c7c74aed11c13803319a))
