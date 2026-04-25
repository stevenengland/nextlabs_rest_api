# Ubiquitous Language

> Canonical domain vocabulary for the NextLabs SDK. When code, docs, or
> conversation drift from these terms, this file wins — update it
> deliberately, not implicitly.
>
> For module layout, public client names, sync/async parity, transport
> stack, and the error-hierarchy escape rule, see
> [`architecture.md`](./architecture.md). This file does not repeat them.

## Products & APIs

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **NextLabs** | The vendor / external authorization platform this SDK targets. | — |
| **CloudAz** | The NextLabs management plane: policies, components, reports, audit logs. | Console, CC, control plane |
| **Console API** | The HTTP API exposed by **CloudAz** for managing policy artifacts. | CloudAz REST, management API |
| **PDP** | Policy Decision Point — the runtime that evaluates **EvalRequests** and returns **Decisions**. | DPC, decision engine |
| **PDP REST API** | The HTTP API exposed by the **PDP** for evaluation and permission queries. | DPC API |
| **Envelope** | The wrapper object the **Console API** puts around responses, carrying a status code and message distinct from the HTTP status. | wrapper response, payload shell |

## Authentication & tokens

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **CloudAzAuth** | The OIDC auth helper that acquires, refreshes, and injects bearer tokens for the **Console API**. | CloudAz authenticator |
| **PdpAuth** | The auth helper for the **PDP**, resolving its **token URL** and obtaining bearer tokens. | DPC auth |
| **StaticTokenAuth** | An auth helper that uses a caller-supplied bearer token verbatim (no refresh). | manual auth |
| **ID token** | The OIDC `id_token` used as the Authorization bearer; falls back to access token with a warning. | JWT, bearer |
| **Refresh token** | The OIDC refresh token used to renew an expired **ID token** without re-prompting. | renewal token |
| **CachedToken** | The persisted token record (id_token, refresh_token, expirations) stored by a **TokenCache**. | token blob |
| **TokenCache** | The pluggable token-store interface (`FileTokenCache`, `NullTokenCache`). | token storage |
| **PDP auth source** | The choice of which token endpoint to use for **PDP** login: `cloudaz` (`/cas/token` on the auth base URL) or `pdp` (`/dpc/oauth` on the PDP URL). | auth flavor |
| **Active account** | The currently selected user/tenant identity used by the CLI to scope token cache lookups. | current user, profile |
| **PDP client ID** | The OAuth client identifier used specifically when authenticating to the **PDP**, separate from the **CloudAz** client ID. | DPC client id |

## Policy authoring (CloudAz domain)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **Policy** | A named rule, owned and versioned, that combines **Components** to permit or deny **Actions** on **Resources** for **Subjects**. | rule, policy doc |
| **PolicyLite** | A trimmed listing projection of a **Policy** (search/index views), without full component bodies. | policy summary |
| **Policy Model** | The schema/template a **Component** or **Policy Obligation** conforms to. | template |
| **Component** | A reusable predicate over **Subjects**, **Resources**, or **Actions**, grouped into **ComponentGroups** inside a **Policy**. | element |
| **ComponentGroup** | A boolean grouping (with an `operator`) of **Components** of a single **ComponentGroupType**. | group |
| **ComponentGroupType** | The role a **ComponentGroup** plays: `SUBJECT`, `RESOURCE`, or `ACTION`. | category, kind |
| **ComponentCondition** | An `attribute operator value` predicate inside a **Component**. | rule, expression |
| **PolicyObligation** | A named side-effect parameterized by a **Policy Model**, attached to allow/deny outcomes of a **Policy**. | obligation rule |
| **Tag** | A typed label (`POLICY_MODEL`, `COMPONENT`, `POLICY`, `FOLDER`) attached to policy artifacts for organization. | label |
| **Folder** | The hierarchical container in which **Policies** and **Components** live. | directory |
| **Deployment** | The act and state of pushing a **Policy** or **Component** revision out to enforcement points. | publish, push |
| **DPS** | A Deployment Push Service target referenced by `dps_url` in **PushResults**. | endpoint URL |

## Authorization runtime (PDP domain)

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **EvalRequest** | A single authorization question sent to the **PDP**: `(Subject, Resource, Action, Application[, Environment])`. | query, request |
| **EvalResult** | The PDP's answer for one **EvalRequest**: a **Decision**, a **Status**, **Obligations**, and matched **PolicyRefs**. | result |
| **EvalResponse** | The envelope holding one or more **EvalResults** for a batch evaluation. | response wrapper |
| **PermissionsRequest** | A "what actions are allowed?" query for a `(Subject, Resource, Application)` tuple. | bulk eval |
| **PermissionsResponse** | The PDP's answer to a **PermissionsRequest**, partitioned into `allowed` / `denied` / `dont_care` **ActionPermissions**. | permission set |
| **Decision** | The XACML verdict: `Permit`, `Deny`, `NotApplicable`, or `Indeterminate`. | outcome, verdict |
| **Status** | The XACML status (code + message + detail) accompanying an **EvalResult**, distinct from the HTTP status. | result code |
| **Subject** | The actor (typically a user or service identity) being evaluated, with `id` and free-form attributes. | principal, requester |
| **Resource** | The target object being acted upon, with `id`, `type`, optional **ResourceDimension**, and attributes. | object, target |
| **Action** | The operation the **Subject** wants to perform on the **Resource**, identified by `id`. | verb, operation |
| **Application** | The calling application context, with `id` and attributes. Required by every **EvalRequest**. | client app |
| **Environment** | Optional contextual attributes (time, location, device) for the evaluation. | context |
| **ResourceDimension** | Marks a **Resource** as the `from` or `to` side of a transfer-style **Action**. | direction |
| **Obligation** | A PDP-issued instruction (with attributes) that the caller must honor when acting on a **Decision**. | post-condition, side-effect |
| **PolicyRef** | A reference (`id`, `version`) to a **Policy** that contributed to an **EvalResult**. | matched policy |
| **ActionPermission** | An `(Action, Obligations, PolicyRefs)` triple inside a **PermissionsResponse** bucket. | allowed action |

## Errors

For the hierarchy root and the rule that only `NextLabsError` subclasses
escape public APIs, see [`architecture.md`](./architecture.md).

| Term | Definition | Aliases to avoid |
| --- | --- | --- |
| **AuthenticationError** | HTTP 401 or token acquisition failure. | auth failure |
| **RefreshTokenExpiredError** | The **refresh token** is no longer usable, either by lifetime or endpoint rejection. Subclass of **AuthenticationError**. | session expired |
| **AuthorizationError** | HTTP 403. | forbidden |
| **PdpStatusError** | HTTP 200 with a non-ok XACML **Status** from the **PDP**. Subclass of **ApiError**. | xacml error |
| **PdpPayloadError** | Local failure to read or parse a PDP request payload file. | payload error |

## Relationships

- A **Policy** belongs to exactly one **Folder** and references many **Components** through **ComponentGroups**.
- A **ComponentGroup** of type `SUBJECT` / `RESOURCE` / `ACTION` constrains the matching dimension of an **EvalRequest**.
- An **EvalRequest** produces exactly one **EvalResult**; an **EvalResponse** carries one or more.
- An **EvalResult** carries exactly one **Decision** and one **Status**, plus zero or more **Obligations** and **PolicyRefs**.
- A **CachedToken** is owned by exactly one **Active account** and stored by exactly one **TokenCache**.
- The **PDP auth source** determines which **token URL** **PdpAuth** uses; **CloudAzAuth** is unaffected.

## Example dialogue

> **Dev:** "When I send an **EvalRequest** with a **Subject** and a `from` **Resource**, what does the **PDP** return if no **Policy** matches?"
>
> **Domain expert:** "You'll get an **EvalResult** with **Decision** `NotApplicable` and an empty **PolicyRefs** list — that's not an error, just a well-formed 'no rule applied'. A non-ok **Status** on HTTP 200 is different: that surfaces as a **PdpStatusError**."
>
> **Dev:** "And the **Obligations** on a `Permit` — those come from the **PolicyObligations** authored on the **Policy**?"
>
> **Domain expert:** "Right. Each matching **Policy** contributes its allow- or deny-side **PolicyObligations**, which the PDP renders as runtime **Obligations** on the **EvalResult**. The caller must honor them; the SDK just deserializes them."
>
> **Dev:** "If the **CloudAzAuth** **refresh token** has expired, do my **PdpClient** calls also fail?"
>
> **Domain expert:** "Only if your **PDP auth source** is `cloudaz` and you share the same **Active account**. With `pdp`, the **PdpAuth** hits `/dpc/oauth` on the **PDP URL** with its own **PDP client ID**, so the two token lifecycles are independent."

## Flagged ambiguities

- **"Component"** is overloaded. In CloudAz it is the policy-authoring predicate (`Component`, `ComponentLite`, `PolicyComponentRef`); in general software speak it can mean any module. Keep **Component** for the policy artifact only; for code modules say "module" or name the file.
- **"Policy"** vs **"PolicyRef"** vs **"PolicyLite"**. **Policy** is the full authored artifact. **PolicyLite** is the listing projection. **PolicyRef** is a runtime pointer (`id`, `version`) returned by the **PDP**. Don't use "policy" for any of the latter two without qualification.
- **"Status"** is overloaded across HTTP, the CloudAz **Envelope**, and XACML on **EvalResult**. Always qualify: **HTTP status**, **envelope status**, or (XACML) **Status**.
- **"Auth"** as a bare noun is ambiguous between **CloudAzAuth**, **PdpAuth**, **StaticTokenAuth**, and the **PDP auth source** flag. Name the specific helper or say **PDP auth source** for the flag.
- **"Token"** without a qualifier is ambiguous between **ID token**, access token, **refresh token**, and **CachedToken**. Always qualify.
- **"Account"** vs **"User"** vs **"Subject"**. **Active account** is the CLI-side selected identity used for token cache scoping. A **Subject** is the PDP-side actor in an **EvalRequest**. They are not the same thing — an **Active account** drives outbound auth; a **Subject** is the authorization question's `who`.
- **"Application"** in a **PermissionsRequest**/**EvalRequest** is the *calling* business application context, not this SDK and not the **Console API** caller. Don't conflate it with the OAuth client.
- **"Client"** is overloaded between OAuth client (credentials) and SDK client (**CloudAzClient**, **PdpClient**). Say **OAuth client** or name the SDK class.
- **"Deployment"** in CloudAz means policy push to enforcement points, not application deployment. When discussing CI/CD, say "release" or "publish" instead.
