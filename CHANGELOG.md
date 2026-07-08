# Changelog

## 0.14.1 - 2026-07-08

### nextlabs-sdk 0.14.1

#### Bug Fixes

- fix(search): make scim2-filter-parser CLI-only again @stevenengland ([#306](https://github.com/stevenengland/nextlabs_rest_api/pull/306))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.14.0...0.14.1

## 0.14.0 - 2026-07-01

### nextlabs-sdk 0.14.0

#### Features

- feat(cli): add components history and view-revision commands (#<!---->192) @stevenengland ([#295](https://github.com/stevenengland/nextlabs_rest_api/pull/295))
- feat(cli): surface remembered plaintext choice in auth status @stevenengland ([#289](https://github.com/stevenengland/nextlabs_rest_api/pull/289))
- feat(token-cache): remember plaintext-storage choice across CLI runs @stevenengland ([#288](https://github.com/stevenengland/nextlabs_rest_api/pull/288))
- feat(token-cache): state-aware plaintext hints and lockout guard @stevenengland ([#287](https://github.com/stevenengland/nextlabs_rest_api/pull/287))
- feat(diff): element-count marker on list-typed field headers @stevenengland ([#281](https://github.com/stevenengland/nextlabs_rest_api/pull/281))
- feat(policy-diff): expand added/removed obligation content in semantic diff @stevenengland ([#280](https://github.com/stevenengland/nextlabs_rest_api/pull/280))
- feat(cli): report token cache encryption in auth status @stevenengland ([#262](https://github.com/stevenengland/nextlabs_rest_api/pull/262))
- feat(token-cache): interactive TTY passphrase source and plaintext confirmation gate @stevenengland ([#260](https://github.com/stevenengland/nextlabs_rest_api/pull/260))
- feat(token-cache): add keyring passphrase source with raw KEK @stevenengland ([#259](https://github.com/stevenengland/nextlabs_rest_api/pull/259))
- feat(token-cache): encrypt CLI token cache at rest via NEXTLABS_MASTER_PASSWORD @stevenengland ([#258](https://github.com/stevenengland/nextlabs_rest_api/pull/258))

#### Bug Fixes

- fix(diff): hide noise-subtree changes at any path segment (#<!---->293) @stevenengland ([#294](https://github.com/stevenengland/nextlabs_rest_api/pull/294))
- fix(PRD): #<!---->282 cleanup — capstone findings @stevenengland ([#291](https://github.com/stevenengland/nextlabs_rest_api/pull/291))
- fix(token-cache): degrade to plaintext on a non-seekable controlling tty @stevenengland ([#279](https://github.com/stevenengland/nextlabs_rest_api/pull/279))
- fix(token-cache): address #<!---->263 second-pass review findings @stevenengland ([#271](https://github.com/stevenengland/nextlabs_rest_api/pull/271))
- fix(cli): add **main** guard so debugger can attach to entrypoint @stevenengland ([#268](https://github.com/stevenengland/nextlabs_rest_api/pull/268))

#### Documentation

- docs: document token-cache encryption and remembered choice (#<!---->286) @stevenengland ([#290](https://github.com/stevenengland/nextlabs_rest_api/pull/290))

#### Maintenance

<details>
<summary>4 changes</summary>
- refactor(search): mark payload label constants private (#<!---->263) @stevenengland ([#273](https://github.com/stevenengland/nextlabs_rest_api/pull/273))
- test(policy-diff): split test_cli_policy_diff into themed modules (#<!---->263 F4) @stevenengland ([#275](https://github.com/stevenengland/nextlabs_rest_api/pull/275))
- test(policy-diff): split test_cli_policy_diff into themed modules (#<!---->263 F4) @stevenengland ([#272](https://github.com/stevenengland/nextlabs_rest_api/pull/272))
- test(token-cache): verify organic legacy→encrypted migration (#<!---->134) @stevenengland ([#261](https://github.com/stevenengland/nextlabs_rest_api/pull/261))
</details>
**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.13.0...0.14.0
## 0.13.0 - 2026-06-26

### nextlabs-sdk 0.13.0

#### Features

- feat(cli): add --criteria-file, multi --sort and --page-no to policies search @stevenengland ([#253](https://github.com/stevenengland/nextlabs_rest_api/pull/253))
- feat(search): complete --where with nested, date and text match types (#<!---->231) @stevenengland ([#252](https://github.com/stevenengland/nextlabs_rest_api/pull/252))
- feat(search): add --where SCIM filter to policies search (#<!---->230) @stevenengland ([#251](https://github.com/stevenengland/nextlabs_rest_api/pull/251))
- feat(search): add nested, date and text field value shapes (#<!---->229) @stevenengland ([#250](https://github.com/stevenengland/nextlabs_rest_api/pull/250))
- feat(cli): add --field expression option to policies search (#<!---->228) @stevenengland ([#249](https://github.com/stevenengland/nextlabs_rest_api/pull/249))
- feat(search): scaffold _search package and add SearchExpressionError (#<!---->227) @stevenengland ([#248](https://github.com/stevenengland/nextlabs_rest_api/pull/248))
- feat(diff): cross-policy diff core (diff A B) @stevenengland ([#244](https://github.com/stevenengland/nextlabs_rest_api/pull/244))
- feat(diff): render grouping drift in unified format with semantic parity (#<!---->237) @stevenengland ([#239](https://github.com/stevenengland/nextlabs_rest_api/pull/239))
- feat(diff): operator/grouping-aware compare_slot for policies diff @stevenengland ([#238](https://github.com/stevenengland/nextlabs_rest_api/pull/238))
- feat(cli): add identity header to policies diff output (#<!---->225) @stevenengland ([#234](https://github.com/stevenengland/nextlabs_rest_api/pull/234))

#### Bug Fixes

- fix(PRD): #<!---->226 cleanup — capstone findings @stevenengland ([#255](https://github.com/stevenengland/nextlabs_rest_api/pull/255))
- fix(PRD): #<!---->241 cleanup — capstone findings @stevenengland ([#246](https://github.com/stevenengland/nextlabs_rest_api/pull/246))
- fix(PRD): #<!---->235 cleanup — capstone findings @stevenengland ([#240](https://github.com/stevenengland/nextlabs_rest_api/pull/240))

#### Documentation

- docs(search): document policy-search expressions and mark ADR 0004 implemented @stevenengland ([#254](https://github.com/stevenengland/nextlabs_rest_api/pull/254))

#### Maintenance

- test(diff): cross-policy --show-all identity reveal (241/2) @stevenengland ([#245](https://github.com/stevenengland/nextlabs_rest_api/pull/245))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.12.1...0.13.0

## 0.12.1 - 2026-06-23

### nextlabs-sdk 0.12.1

#### Bug Fixes

- fix: remove typer._click private-internal coupling from _error_handler @stevenengland ([#218](https://github.com/stevenengland/nextlabs_rest_api/pull/218))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.12.0...0.12.1

## 0.12.0 - 2026-06-22

### nextlabs-sdk 0.12.0

#### Features

- feat(cli-diff): semantic policy-diff legibility (#<!---->212) @stevenengland ([#213](https://github.com/stevenengland/nextlabs_rest_api/pull/213))
- feat(cli): show help instead of error for incomplete commands @stevenengland ([#206](https://github.com/stevenengland/nextlabs_rest_api/pull/206))
- feat(cli): json delta output and --exit-code for policies diff (#<!---->199) @stevenengland ([#204](https://github.com/stevenengland/nextlabs_rest_api/pull/204))
- feat(cli): add --format option with unified diff for policies diff @stevenengland ([#203](https://github.com/stevenengland/nextlabs_rest_api/pull/203))
- feat(cli): compare allow and deny obligations in policy diff @stevenengland ([#202](https://github.com/stevenengland/nextlabs_rest_api/pull/202))
- feat(cli): match policy component slots by schema-type identity (194/2) @stevenengland ([#201](https://github.com/stevenengland/nextlabs_rest_api/pull/201))
- feat(cli): policies diff — end-to-end semantic diff (194/1) @stevenengland ([#200](https://github.com/stevenengland/nextlabs_rest_api/pull/200))
- feat(cli): add policies history and view-revision commands (#<!---->191) @stevenengland ([#193](https://github.com/stevenengland/nextlabs_rest_api/pull/193))

#### Bug Fixes

- fix(cli): fetch policy diff revisions by entry id (#<!---->209) @stevenengland ([#210](https://github.com/stevenengland/nextlabs_rest_api/pull/210))
- fix(PRD): #<!---->194 cleanup — capstone findings @stevenengland ([#205](https://github.com/stevenengland/nextlabs_rest_api/pull/205))
- fix(deps): bump actions/checkout from 6 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) ([#190](https://github.com/stevenengland/nextlabs_rest_api/pull/190))

#### Dependencies

- fix(deps): bump actions/checkout from 6 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) ([#190](https://github.com/stevenengland/nextlabs_rest_api/pull/190))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.11.0...0.12.0

## 0.11.0 - 2026-06-11

### nextlabs-sdk 0.11.0

#### Features

- feat(cloudaz): add component revision history (list_history + get_revision) @stevenengland ([#187](https://github.com/stevenengland/nextlabs_rest_api/pull/187))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.10.0...0.11.0

## 0.10.0 - 2026-06-11

### nextlabs-sdk 0.10.0

#### Features

- feat(cloudaz): add get_revision + PolicyRevision (#<!---->173) @stevenengland ([#176](https://github.com/stevenengland/nextlabs_rest_api/pull/176))
- feat(cloudaz): add policy revision history (list_history) (#<!---->172) @stevenengland ([#175](https://github.com/stevenengland/nextlabs_rest_api/pull/175))

#### Bug Fixes

- fix(PRD): #<!---->170 cleanup — capstone findings @stevenengland ([#180](https://github.com/stevenengland/nextlabs_rest_api/pull/180))

#### Documentation

- docs(cloudaz): record viewRevision endpoint in vendor_gaps @stevenengland ([#177](https://github.com/stevenengland/nextlabs_rest_api/pull/177))

#### Maintenance

- build(devcontainer): migrate to docker-compose style @stevenengland ([#181](https://github.com/stevenengland/nextlabs_rest_api/pull/181))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.9.1...0.10.0

## 0.9.1 - 2026-06-08

### nextlabs-sdk 0.9.1

#### Bug Fixes

- fix(cloudaz): accept null owner/modifier metadata on Component/Policy models @stevenengland ([#166](https://github.com/stevenengland/nextlabs_rest_api/pull/166))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.9.0...0.9.1

## 0.9.0 - 2026-06-08

### nextlabs-sdk 0.9.0

#### Features

- feat(cloudaz): interpret no-data envelope by call shape (#<!---->159) @stevenengland ([#161](https://github.com/stevenengland/nextlabs_rest_api/pull/161))

#### Bug Fixes

- fix(cloudaz): accept live API shapes for Component/Policy fields @stevenengland ([#163](https://github.com/stevenengland/nextlabs_rest_api/pull/163))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.8.0...0.9.0

## 0.8.0 - 2026-06-01

### nextlabs-sdk 0.8.0

#### Features

- feat(pdp): add **all** to PDP facade + verification test @stevenengland ([#150](https://github.com/stevenengland/nextlabs_rest_api/pull/150))
- feat(cloudaz): re-export missing models and services via public facade @stevenengland ([#149](https://github.com/stevenengland/nextlabs_rest_api/pull/149))

#### Bug Fixes

- fix(PRD): #<!---->143 cleanup — capstone findings @stevenengland ([#154](https://github.com/stevenengland/nextlabs_rest_api/pull/154))

#### Documentation

- docs(adr): add public API surface decision record (#<!---->146) @stevenengland ([#151](https://github.com/stevenengland/nextlabs_rest_api/pull/151))

#### Maintenance

- refactor(tests): migrate test imports to public facades (#<!---->148) @stevenengland ([#153](https://github.com/stevenengland/nextlabs_rest_api/pull/153))
- refactor(sdk): import clients from public facades + **all** + export test @stevenengland ([#152](https://github.com/stevenengland/nextlabs_rest_api/pull/152))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.7.0...0.8.0

## 0.7.0 - 2026-05-30

### nextlabs-sdk 0.7.0

#### Features

- feat(cloudaz): re-export component, policy models and services @stevenengland ([#139](https://github.com/stevenengland/nextlabs_rest_api/pull/139))
- feat(cli): friendly error + toDate/header defaults for activity-logs @stevenengland ([#125](https://github.com/stevenengland/nextlabs_rest_api/pull/125))
- feat(cli): inline flags for activity-logs search/export @stevenengland ([#124](https://github.com/stevenengland/nextlabs_rest_api/pull/124))

#### Bug Fixes

- fix(cli): relax activity-logs inline defaults for live reporters @stevenengland ([#127](https://github.com/stevenengland/nextlabs_rest_api/pull/127))
- fix(cli): narrow activity-logs default header to spec-example columns @stevenengland ([#126](https://github.com/stevenengland/nextlabs_rest_api/pull/126))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.6.0...0.7.0

## 0.6.0 - 2026-04-24

### nextlabs-sdk 0.6.0

#### Features

- feat(cloudaz)!: send access_token as bearer credential @stevenengland ([#120](https://github.com/stevenengland/nextlabs_rest_api/pull/120))
- feat(cloudaz): publicly re-export ReporterAuditLogEntry, SavedSearch, SearchCriteria @stevenengland ([#113](https://github.com/stevenengland/nextlabs_rest_api/pull/113))
- feat(cli): accept ISO and relative dates for time-range options @stevenengland ([#82](https://github.com/stevenengland/nextlabs_rest_api/pull/82))
- feat(tools): accept targeted paths in checks.py and tests.py @stevenengland ([#81](https://github.com/stevenengland/nextlabs_rest_api/pull/81))

#### Bug Fixes

- fix(cli): add wide-output columns to cloudaz table commands @stevenengland ([#121](https://github.com/stevenengland/nextlabs_rest_api/pull/121))
- fix(cli): preserve persisted verify_ssl on silent re-login @stevenengland ([#119](https://github.com/stevenengland/nextlabs_rest_api/pull/119))
- fix(envelope): emit debug log naming each decode failure mode @stevenengland ([#114](https://github.com/stevenengland/nextlabs_rest_api/pull/114))
- fix(pdp): declare xmlns:xsi and xsi:schemaLocation on XACML Request @stevenengland ([#112](https://github.com/stevenengland/nextlabs_rest_api/pull/112))
- fix(auth): use monotonic clock for CloudAz in-memory token expiry @stevenengland ([#111](https://github.com/stevenengland/nextlabs_rest_api/pull/111))
- fix(retry): support RFC 7231 HTTP-date Retry-After header @stevenengland ([#110](https://github.com/stevenengland/nextlabs_rest_api/pull/110))
- fix(cloudaz-auth): require id_token by default, opt-in access_token fallback @stevenengland ([#109](https://github.com/stevenengland/nextlabs_rest_api/pull/109))
- fix(pdp): emit IncludeInResult="false" on every request attribute @stevenengland ([#108](https://github.com/stevenengland/nextlabs_rest_api/pull/108))
- fix(cloudaz): send pageSize and showHidden on tag and saved-search endpoints @stevenengland ([#107](https://github.com/stevenengland/nextlabs_rest_api/pull/107))
- fix(cloudaz): align ComponentLite and Tag required fields with OpenAPI @stevenengland ([#106](https://github.com/stevenengland/nextlabs_rest_api/pull/106))
- fix(cloudaz): add FOLDER_TAG to TagType enum @stevenengland ([#105](https://github.com/stevenengland/nextlabs_rest_api/pull/105))
- fix(cloudaz): preserve aggregators, save_info, and widget key on report models @stevenengland ([#104](https://github.com/stevenengland/nextlabs_rest_api/pull/104))
- fix(cloudaz): add shared field to DeleteReportsRequest @stevenengland ([#103](https://github.com/stevenengland/nextlabs_rest_api/pull/103))
- fix(cloudaz): align ActivityLogQuery required fields with OpenAPI @stevenengland ([#102](https://github.com/stevenengland/nextlabs_rest_api/pull/102))
- fix(cli): apply reporter-required defaults on audit-logs search @stevenengland ([#101](https://github.com/stevenengland/nextlabs_rest_api/pull/101))
- fix(cloudaz): parse bare Spring Pageable for reporter audit-logs search @stevenengland ([#83](https://github.com/stevenengland/nextlabs_rest_api/pull/83))

#### Maintenance

- test(cloudaz): verify pagination envelope + zero-indexed pageNo across endpoint families @stevenengland ([#117](https://github.com/stevenengland/nextlabs_rest_api/pull/117))
- test(openapi): parity checks for required, properties, enums on DTOs @stevenengland ([#116](https://github.com/stevenengland/nextlabs_rest_api/pull/116))
- style(token-cache): make NullTokenCache stub bodies explicit with ... @stevenengland ([#115](https://github.com/stevenengland/nextlabs_rest_api/pull/115))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.4.0...0.6.0

## 0.4.0 - 2026-04-23

### nextlabs-sdk 0.4.0

#### Features

- feat(pdp): surface non-ok XACML Status as PdpStatusError @stevenengland ([#77](https://github.com/stevenengland/nextlabs_rest_api/pull/77))
- feat(cli): pretty-print JSON and allow suppressing truncation in -vv trace @stevenengland ([#74](https://github.com/stevenengland/nextlabs_rest_api/pull/74))
- feat(pdp): surface XACML StatusDetail in eval responses @stevenengland ([#71](https://github.com/stevenengland/nextlabs_rest_api/pull/71))
- feat(pdp): support file-based request payloads (JSON/YAML/XACML) — implements #<!---->65 tracer bullets @stevenengland ([#70](https://github.com/stevenengland/nextlabs_rest_api/pull/70))
- feat(cli): interactive SSL retry on `nextlabs auth login` @stevenengland ([#64](https://github.com/stevenengland/nextlabs_rest_api/pull/64))

#### Bug Fixes

- fix(pdp): correct permissions endpoint, serialization, and response parser; add 'pdp explain' CLI @stevenengland ([#76](https://github.com/stevenengland/nextlabs_rest_api/pull/76))
- fix(pdp): send required Service and Version headers @stevenengland ([#72](https://github.com/stevenengland/nextlabs_rest_api/pull/72))
- fix(cli): collect PDP client-id and surface real OAuth errors (#<!---->61) @stevenengland ([#62](https://github.com/stevenengland/nextlabs_rest_api/pull/62))
- feat(cli)!: add --pdp-auth to pick CloudAz or PDP token endpoint @stevenengland ([#55](https://github.com/stevenengland/nextlabs_rest_api/pull/55))
- fix(deps): bump actions/setup-python from 5 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) ([#48](https://github.com/stevenengland/nextlabs_rest_api/pull/48))
- fix(deps): bump release-drafter/release-drafter from 6 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) ([#49](https://github.com/stevenengland/nextlabs_rest_api/pull/49))
- fix(pdp)!: default token URL to /dpc/oauth; add auth_base_url kwarg @stevenengland ([#54](https://github.com/stevenengland/nextlabs_rest_api/pull/54))
- fix(cloudaz): surface envelope message on non-2xx HTTP responses @stevenengland ([#46](https://github.com/stevenengland/nextlabs_rest_api/pull/46))

#### Dependencies

- fix(deps): bump actions/setup-python from 5 to 6 @[dependabot[bot]](https://github.com/apps/dependabot) ([#48](https://github.com/stevenengland/nextlabs_rest_api/pull/48))
- fix(deps): bump release-drafter/release-drafter from 6 to 7 @[dependabot[bot]](https://github.com/apps/dependabot) ([#49](https://github.com/stevenengland/nextlabs_rest_api/pull/49))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.3.0...0.4.0

## 0.3.0 - 2026-04-20

### nextlabs-sdk 0.3.0

#### Features

- feat(cli): graceful re-auth when refresh token expires @stevenengland ([#43](https://github.com/stevenengland/nextlabs_rest_api/pull/43))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/0.2.1...0.3.0

## 0.2.0 - 2026-04-19

### nextlabs-sdk 0.2.0

#### Features

- feat(cli): PRD #<!---->11 part 2 — CLI parity for P2–P5 (sub-issues #<!---->19–#<!---->27) @stevenengland ([#30](https://github.com/stevenengland/nextlabs_rest_api/pull/30))

#### Bug Fixes

- fix(cli): use cached refresh token before demanding password @stevenengland ([#34](https://github.com/stevenengland/nextlabs_rest_api/pull/34))
- fix(http): clamp Retry-After and extract RetryPolicy @stevenengland ([#32](https://github.com/stevenengland/nextlabs_rest_api/pull/32))

#### Documentation

- docs: rewrite README with hard-forked SDK/CLI sections, demo, and recipes @stevenengland ([#35](https://github.com/stevenengland/nextlabs_rest_api/pull/35))

#### Maintenance

- test(e2e): two-layer E2E testing strategy (OpenAPI round-trip + WireMock) @stevenengland ([#31](https://github.com/stevenengland/nextlabs_rest_api/pull/31))

**Full Changelog**: https://github.com/stevenengland/nextlabs_rest_api/compare/...0.2.0
