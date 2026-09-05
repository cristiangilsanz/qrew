# Changelog

## [1.2.0](https://github.com/cristiangilsanz/qrew/compare/qrew/v1.1.1...qrew/v1.2.0) (2026-09-05)


### Features

* close the gaps between what the server does and what the app offers ([#288](https://github.com/cristiangilsanz/qrew/issues/288)) ([bc41ed5](https://github.com/cristiangilsanz/qrew/commit/bc41ed5602a99cec79d417bdab2e4dae51e11fbe))
* implement authentication feature (login + register) ([#257](https://github.com/cristiangilsanz/qrew/issues/257)) ([a2b31d9](https://github.com/cristiangilsanz/qrew/commit/a2b31d9e0754bdf011bc167504e3ab2b7c594775))
* implement events discovery and detail pages ([#262](https://github.com/cristiangilsanz/qrew/issues/262)) ([3a8414a](https://github.com/cristiangilsanz/qrew/commit/3a8414a3f99fd874416cae34c4a977819c73f9da))
* implement my tickets list and QR code display ([#268](https://github.com/cristiangilsanz/qrew/issues/268)) ([634fa42](https://github.com/cristiangilsanz/qrew/commit/634fa426f15a39b419b4a1a342d05141853c633e))
* implement organisation and event management ([#263](https://github.com/cristiangilsanz/qrew/issues/263)) ([a04cd6f](https://github.com/cristiangilsanz/qrew/commit/a04cd6fa948f1b0c6d825efdcbb7ae52707eec72))
* implement passkey registration and authentication ([#260](https://github.com/cristiangilsanz/qrew/issues/260)) ([960b102](https://github.com/cristiangilsanz/qrew/commit/960b102123c643a1accf24ad85f19ca7c15968a3))
* implement post-login onboarding flow ([#259](https://github.com/cristiangilsanz/qrew/issues/259)) ([b88df53](https://github.com/cristiangilsanz/qrew/commit/b88df531e2909da607151600b4c1a7d852aaf15a))
* implement profile and account management ([#261](https://github.com/cristiangilsanz/qrew/issues/261)) ([5d69c02](https://github.com/cristiangilsanz/qrew/commit/5d69c02c0b0ba48618b17fd4aa55fbe0d292b817))
* implement queue, reservation, and payment flow ([#267](https://github.com/cristiangilsanz/qrew/issues/267)) ([1d2397d](https://github.com/cristiangilsanz/qrew/commit/1d2397d0ce3eb8e55ce982a20c69cf1de2e0b7eb))
* implement websocket realtime client ([#269](https://github.com/cristiangilsanz/qrew/issues/269)) ([80fc902](https://github.com/cristiangilsanz/qrew/commit/80fc90234d38deecdf2e86dfca958ebf4b83f83b))
* let the app trust the device it runs on ([#282](https://github.com/cristiangilsanz/qrew/issues/282)) ([99a092b](https://github.com/cristiangilsanz/qrew/commit/99a092b822d0f38764043d29f5050eddaca592d4))
* publish domain events through a transactional outbox and split the stack into networks ([#293](https://github.com/cristiangilsanz/qrew/issues/293)) ([219684a](https://github.com/cristiangilsanz/qrew/commit/219684a30e678d2869a9de5dfbb2b6e91c76d0a9))
* put every confirmation behind one dialog and every empty list behind one line ([#280](https://github.com/cristiangilsanz/qrew/issues/280)) ([79124c3](https://github.com/cristiangilsanz/qrew/commit/79124c3b952c371720989afabf9b1ba3b01c6387))
* require the passkey before a ticket shows its code ([#283](https://github.com/cristiangilsanz/qrew/issues/283)) ([62b2f4a](https://github.com/cristiangilsanz/qrew/commit/62b2f4aa37fcbfa49b64a9e0a4f09c44e092c271))
* show the picked document on the lost device screen ([#291](https://github.com/cristiangilsanz/qrew/issues/291)) ([b3c6f8c](https://github.com/cristiangilsanz/qrew/commit/b3c6f8c473c38c07e91308972e8f42963ff2e8c7))
* trust one device per account and recover it from inside the app ([#290](https://github.com/cristiangilsanz/qrew/issues/290)) ([15d4461](https://github.com/cristiangilsanz/qrew/commit/15d446197cb4f8061787430aefd4496f4fc428c6))
* UI refinement and polish (QRW-255) ([#271](https://github.com/cristiangilsanz/qrew/issues/271)) ([e47f4cd](https://github.com/cristiangilsanz/qrew/commit/e47f4cd57824b6fdbd40f4bd167dee5bdff47b75))


### Bug Fixes

* describe the domain events the system actually publishes ([#295](https://github.com/cristiangilsanz/qrew/issues/295)) ([5cff62e](https://github.com/cristiangilsanz/qrew/commit/5cff62e258eeb93e3721364e2e4451ca5626dd52))
* drop the rejection reason the mail never showed and leave for login on delete ([#275](https://github.com/cristiangilsanz/qrew/issues/275)) ([f6cafd2](https://github.com/cristiangilsanz/qrew/commit/f6cafd24498b4ec28aa2d04d5960d3e8fefb56b3))
* give audit the same probes as every other service ([#285](https://github.com/cristiangilsanz/qrew/issues/285)) ([2a6916a](https://github.com/cristiangilsanz/qrew/commit/2a6916ae92d8560c29c0132110e7b0701b234675))
* give the audit image the packages its service now needs ([#286](https://github.com/cristiangilsanz/qrew/issues/286)) ([1ad8d21](https://github.com/cristiangilsanz/qrew/commit/1ad8d21d2798abe750d66827b7ea1f1892df9961))
* harden credential storage, response headers and secret handling ([#272](https://github.com/cristiangilsanz/qrew/issues/272)) ([1cc1b3b](https://github.com/cristiangilsanz/qrew/commit/1cc1b3b739d798153390ce4daf99e16ebb864032))
* harden the dev stack and standardise error and toast messaging ([#273](https://github.com/cristiangilsanz/qrew/issues/273)) ([6d9c22e](https://github.com/cristiangilsanz/qrew/commit/6d9c22ef6d775d8abd2257a4a8761d0026b428a0))
* let ticket restore honour the granular gate switches ([#287](https://github.com/cristiangilsanz/qrew/issues/287)) ([882834b](https://github.com/cristiangilsanz/qrew/commit/882834b667b6556bb9d092150ad33c70f4021c58))
* **observability:** carry the trace across the broker and the workers ([#297](https://github.com/cristiangilsanz/qrew/issues/297)) ([01fcbc9](https://github.com/cristiangilsanz/qrew/commit/01fcbc9a7a806d11a9852289942b91f9b0af0162))
* organiser bug fixes found during manual testing ([#266](https://github.com/cristiangilsanz/qrew/issues/266)) ([2fe8c0c](https://github.com/cristiangilsanz/qrew/commit/2fe8c0cd9760249e5747ad2beac79335e9f98674))
* **payments:** omit absent payment identifiers from events, rename the edge network to publica ([#296](https://github.com/cristiangilsanz/qrew/issues/296)) ([b71a99a](https://github.com/cristiangilsanz/qrew/commit/b71a99ad957e0e780bfe4910ae039096fb017874))
* print the coverage tables to the log as well as the run summary ([#274](https://github.com/cristiangilsanz/qrew/issues/274)) ([6a32c6a](https://github.com/cristiangilsanz/qrew/commit/6a32c6ad6786e628255af4e415cb0d7a5aee88fb))
* repair the offer screen and settle how labels are capitalised ([#277](https://github.com/cristiangilsanz/qrew/issues/277)) ([da10229](https://github.com/cristiangilsanz/qrew/commit/da1022957e1971e87388ff4b3cf7efabf0e3c8fb))
* restore the ticket state payload and align the docs with what the code publishes ([#294](https://github.com/cristiangilsanz/qrew/issues/294)) ([6fe8502](https://github.com/cristiangilsanz/qrew/commit/6fe85021187c114965c25ea14b0ef7e4707c4b10))
* separate a frozen ticket from a listed one, and unlock a revoked device ([#289](https://github.com/cristiangilsanz/qrew/issues/289)) ([4266e61](https://github.com/cristiangilsanz/qrew/commit/4266e6110b710d2c0908e37080141852d37c5fe7))
* translate the password recovery screens into spanish ([#278](https://github.com/cristiangilsanz/qrew/issues/278)) ([e63cb00](https://github.com/cristiangilsanz/qrew/commit/e63cb007c6ef059348745d917dec14f1495ccd98))


### Documentation

* capitalise env variable descriptions in table ([c988b52](https://github.com/cristiangilsanz/qrew/commit/c988b52cd9dc5fb242a8352a1d68034c3d3c3579))
* center tables and remove parenthetical descriptions ([e02a336](https://github.com/cristiangilsanz/qrew/commit/e02a3365758f9af45a1957e296b44ee1115e0c96))
* move architecture note below diagram, rename link to ARCHITECTURE.md ([4d22da0](https://github.com/cristiangilsanz/qrew/commit/4d22da09e906f1e27b9a9c825f8c5f1294e1aa3b))
* name the seeded accounts as the seed actually creates them ([#276](https://github.com/cristiangilsanz/qrew/issues/276)) ([c13d32c](https://github.com/cristiangilsanz/qrew/commit/c13d32ca3811eff891c59fe9da6f5573916703fc))
* record the page that completes a resale offer ([#281](https://github.com/cristiangilsanz/qrew/issues/281)) ([707b971](https://github.com/cristiangilsanz/qrew/commit/707b9718837d25cf8a65f2589bd257014ed2e2b3))
* replace em dash with hyphen in license line ([ecc490f](https://github.com/cristiangilsanz/qrew/commit/ecc490f5b2dacf9a08e2a79e236faa3e4912d747))
* replace tech stack badges with plain bullet lists ([1015f3a](https://github.com/cristiangilsanz/qrew/commit/1015f3a845541fc79fa89f48e3b8250bb13068ba))
* restore section emojis in tech stack ([14e37c6](https://github.com/cristiangilsanz/qrew/commit/14e37c6aa19af7fce96799f5e07097b6c496ec68))
* restructure tech stack by architectural layer in overview ([5d8337d](https://github.com/cristiangilsanz/qrew/commit/5d8337d76af6102a2c1473d0bda1cd2af33495ba))
* split twilio secrets into separate rows ([a18870e](https://github.com/cristiangilsanz/qrew/commit/a18870ec0fe2ab58f373e05192ef182d99eda4d3))
* use joystick emoji for Android Emulator setup link ([9f3a5df](https://github.com/cristiangilsanz/qrew/commit/9f3a5dfebb6d3682455eea056540447b9f209f96))
* use plug emoji for Android USB setup link ([ef470cc](https://github.com/cristiangilsanz/qrew/commit/ef470ccf44c58bb5c5f7380069270d0053a857cd))

## [1.1.1](https://github.com/cristiangilsanz/qrew/compare/qrew/v1.1.0...qrew/v1.1.1) (2026-07-03)


### Bug Fixes

* pin trivy-action to v0.36.0 instead of [@master](https://github.com/master) ([#243](https://github.com/cristiangilsanz/qrew/issues/243)) ([76e5e48](https://github.com/cristiangilsanz/qrew/commit/76e5e48e30b11a5044cad1a431890887123e59c9))
* upgrade release-please-action to v5 for Node.js 24 compatibility ([#244](https://github.com/cristiangilsanz/qrew/issues/244)) ([c6e3ec8](https://github.com/cristiangilsanz/qrew/commit/c6e3ec85f5ccf200cf9424c55e9c1ee024033f98))

## [1.1.0](https://github.com/cristiangilsanz/qrew/compare/qrew/v1.0.0...qrew/v1.1.0) (2026-07-03)


### Features

* scaffold mobile app project ([#230](https://github.com/cristiangilsanz/qrew/issues/230)) ([a6fa00c](https://github.com/cristiangilsanz/qrew/commit/a6fa00c2c3c5234e2445845100b89a22e375873b))


### Bug Fixes

* add missing shared-python package COPYs to service Dockerfiles ([#242](https://github.com/cristiangilsanz/qrew/issues/242)) ([55a77ee](https://github.com/cristiangilsanz/qrew/commit/55a77ee3c2357baa83b5bfe2cd1aac197687cad9))

## Changelog
