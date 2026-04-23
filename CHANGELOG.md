# Changelog

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
