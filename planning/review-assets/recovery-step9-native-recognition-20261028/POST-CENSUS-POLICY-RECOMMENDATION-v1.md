# Conditional policy recommendation after the one census

This is source-only planning based on the retained [scope addendum](SELF-MODULE-CENSUS-POLICY-SCOPE-ADDENDUM-v1.md), [design](SELF-MODULE-CENSUS-DESIGN-v1.md) and [contract](SELF-MODULE-CENSUS-CONTRACT-v1.json). It assumes no census outcome, changes no policy and authorizes no image inspection, compiler or native call.

**Prefer an explicit trusted-System32 platform boundary if the independently verified census is complete and contains only the exact self/core4 reports plus platform reports.** That is proportionate to testing the effective behavior of the pinned vendor libraries on an explicitly trusted Windows host. It does not establish loaded-image authenticity, an unmodified vendor execution path, absence of compatibility fixes or lifetime module closure. DLL initialization effects remain possible despite zero explicit target C queries in the census.

| Choice | When justified | Minimum work and practical limit |
|---|---|---|
| Trusted System32 platform context | Windows host trust is an accepted assumption; reproducibility concerns the pinned application libraries and declared host context. | Review the complete reported set once. Prospectively freeze the platform boundary across child, parent, contract and protocol. No new platform-image reads are necessary for this assumption. A reported path is metadata, not authentication. |
| Finite extra System32 pins | Exact current-host file reproducibility is itself a requirement. | Review all additions together, then separately authorize one bounded static pin batch on independently approved paths. Hashes identify inspected file bytes; they do not prove the bytes of an already loaded image, all dependencies, initializer behavior or shim causation. Windows servicing may require a new prospective version. |

The platform option must retain exact self/core4 pins and paths. Reject wrong-path core/libomp names and protected llama/ggml/CPU application namespaces **before** considering the System32 exception. Reject every other outside-platform image. Define the path comparison precisely and conservatively; the current census's ASCII/slash comparison is an observational classifier, not filesystem authentication. A complete unknown row never grants eligibility by itself.

Do not select either policy from a partial census, clipped/inconsistent metadata, missing known reports, resource/finalization failure or an unexpected protected-native/outside-platform report. Retain the failed gate and stop this native step. Do not add repeated censuses, baseline/loader traces, guessed additions or a compatibility-forensics project. An expected System32-looking name alone is insufficient, and adding only the previously reported Apphelp name would reproduce the one-name-at-a-time failure pattern.

The next decision should record: the independently verified census artifact hash; which option is selected and its trust/reproducibility assumption; the exact prospectively identical policy in every enforcement layer; and tests for wrong-path/core names, protected prefixes, outside-System32 entries and failure vetoes. Only then prepare the separately reviewed next ABI attempt. Prior failures and their unknown identities remain unchanged. Census completeness supplies no ABI, document/EOG, resource-fit or scientific acceptance, and says nothing about modules loaded by later calls.

No new image or runtime inspection was performed for this recommendation.
