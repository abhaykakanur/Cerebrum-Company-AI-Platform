# Security Policy

Cerebrum handles sensitive organizational knowledge across a multi-tenant
platform. Security issues are treated with the highest priority. This
document defines how to report a vulnerability and what to expect.

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.** Public
disclosure before a fix is available puts every tenant organization at risk.

Instead:

1. Report the vulnerability privately to the project's security contact,
   listed in [CODEOWNERS](.github/CODEOWNERS) (`@security-team` or the
   designated Architecture Owner — see
   `docs/architecture/specification/109_Project_Governance.md`).
2. If your platform's private vulnerability reporting feature is enabled on
   this repository, use it in preference to email.
3. Include, where possible: a description of the vulnerability, steps to
   reproduce, the affected component (see
   `docs/architecture/specification/79_Threat_Model.md` for the threat
   categories this platform tracks), and its potential impact.

## Response Process

This repository's security response process is governed by
`docs/architecture/specification/75_Security_Architecture.md` (Audit Logging,
Secrets Management) and `docs/architecture/specification/79_Threat_Model.md`
(the eleven tracked threat categories and their mitigations).

- Reports are acknowledged as soon as practicable.
- Confirmed vulnerabilities are triaged by severity and remediated per the
  Vulnerability Management process
  (`docs/architecture/specification/79_Threat_Model.md`, FR-SC-005).
- Customer notification for a confirmed incident affecting tenant data
  follows the Security Incident Response policy (FR-SC-006) — the specific
  notification timeline is tracked as an open item, see
  `docs/architecture/specification/40_Open_Questions.md`, Open Question 35.

## Scope

This policy covers the Cerebrum platform itself (backend, frontend, shared
packages, infrastructure configuration in this repository). It does not
cover the security posture of third-party connector source systems or LLM
providers Cerebrum integrates with — see
`docs/architecture/specification/60_AI_Model_Abstraction.md` and
`docs/architecture/specification/65_Connector_Architecture.md` for the
boundary of what this platform is responsible for versus the external
systems it connects to.

## Supported Versions

This project has not yet reached its first tagged release. Once versioned
releases begin, this section will list which versions receive security
fixes, consistent with the API Versioning Policy in
`docs/architecture/specification/81_API_Standards.md`.

## Recognition

Responsible disclosure is appreciated. Once a formal acknowledgment process
exists, it will be documented here.
