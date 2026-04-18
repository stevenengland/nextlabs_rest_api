# Security policy

## Reporting a vulnerability

Please **do not** report security vulnerabilities through public GitHub
issues, discussions, or pull requests.

Use GitHub's [private vulnerability reporting][pvr] for this repository:

> Repository → **Security** tab → **Report a vulnerability**

[pvr]: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability

You can expect an initial acknowledgement within a few days. We will
work with you to confirm the issue, prepare a fix, and coordinate
disclosure.

## Supported versions

`nextlabs-sdk` is currently in **alpha**. Only the latest release on
PyPI receives security fixes; there is no long-term-support branch yet.
Once the project reaches `1.0.0`, this policy will be updated to list
supported version ranges.

## Scope

In scope:

- The published `nextlabs-sdk` package on PyPI.
- The `nextlabs` CLI shipped with the `[cli]` extra.

Out of scope:

- Issues in the upstream NextLabs CloudAz Console or PDP services
  themselves — please report those directly to NextLabs.
- Vulnerabilities in third-party dependencies that have not yet been
  patched upstream (we will track and update once a fix is available).
