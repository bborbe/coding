# Teamvault conventions

Teamvault is the secret-storage backend used by the `bborbe` cluster. Secrets are stored in teamvault and referenced from configs via short alphanumeric **lookup keys** — NOT by storing the secret itself in the config.

This guide exists so readers + reviewers + AI agents don't flag teamvault lookup keys as exposed credentials.

## The shape

A teamvault lookup key is a **short alphanumeric string** (typically 6-12 chars, base62-like) that identifies a secret entry inside teamvault.

| Format | Examples |
|---|---|
| `[A-Za-z0-9]{6,12}` | `kLoejw`, `eqKj8L`, `9qNBoq`, `Qqap6L`, `xwXZjL` |

Real PEM keys, OAuth tokens, JWT secrets, database passwords, etc. are 100+ characters of base64 / hex / PEM-armored content. Anything that fits in a tweet is a lookup key.

## How keys resolve to secrets

Three template functions consumed by `teamvault-config-parser` (run during `kubectl apply`):

| Function | What it returns |
|---|---|
| `teamvaultFileBase64` | base64-encoded file content (PEM keys, certificates, JSON keyfiles) |
| `teamvaultPassword` | raw password / token string |
| `teamvaultConfig` | structured config blob (e.g. `.netrc` body) |

**Example — `k8s/<service>-secret.yaml`:**

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: maintainer-watcher-github-pr
data:
  PEM_KEY: '{{ "WATCHER_GITHUB_PR_PEM_KEY" | env | teamvaultFileBase64 }}'
```

Read this as: "Look up env var `WATCHER_GITHUB_PR_PEM_KEY` (which holds a teamvault lookup key like `kLoejw`); resolve that key against teamvault to get the actual PEM file; base64-encode the file content; that's the k8s Secret data."

The raw secret never leaves teamvault → operator workstation → cluster. The env file only holds the lookup key.

## Naming convention

Teamvault-resolved env vars use a `_KEY` suffix:

| Env var | Resolves to |
|---|---|
| `WATCHER_GITHUB_PR_PEM_KEY` | GitHub App PEM |
| `AGENT_PR_REVIEWER_PEM_KEY` | GitHub App PEM |
| `GIT_SSH_KEY` | SSH deploy key |
| `SENTRY_DSN_KEY` | Sentry DSN |
| `GEMINI_API_KEY_KEY` | Gemini API token |
| `WATCHER_GITHUB_RELEASE_PEM_KEY` | GitHub App PEM (new) |

**Exception:** some env vars without `_KEY` suffix are also teamvault keys when consumed by a `teamvault*` template function. The template usage is the authoritative signal.

## What this looks like in an .env file

```bash
# dev.env / prod.env header convention:
#
# IMPORTANT: WATCHER_*_PEM_KEY, AGENT_*_PEM_KEY, *_KEY (and any value
# consumed by teamvaultXxx template functions in k8s/*-secret.yaml) are
# TEAMVAULT LOOKUP KEYS, NOT raw secrets. ~6-12 chars. The real secret
# material lives in teamvault and is fetched at `kubectl apply` time by
# the teamvault-config-parser. Do NOT replace these with literal secrets.

export WATCHER_GITHUB_PR_PEM_KEY=kLoejw       # teamvault key → real PEM in cluster
export WATCHER_GITHUB_PR_APP_ID=3798945       # NOT a teamvault key (numeric ID)
export GIT_SSH_KEY=9qNBoq                     # teamvault key → SSH deploy key
```

### RULE teamvault/short-alphanumeric-is-lookup-key-not-secret (MUST)

**Owner**: go-security-specialist
**Applies when**: a code-review agent or security-lint pass flags a 6-12 char alphanumeric value in a `.env` file / k8s manifest / config file as an exposed credential, when the corresponding k8s manifest uses `teamvaultFileBase64` / `teamvaultPassword` / `teamvaultConfig` template functions to resolve the value.
**Enforcement**: judgment (semantic — distinguishing a lookup key from a real short token requires reading the k8s manifest the env var feeds into)
**Why**: Teamvault lookup keys are `[A-Za-z0-9]{6,12}` identifiers, NOT secrets. The real secret material lives in teamvault; the lookup key resolves to it at `kubectl apply` time. Flagging lookup keys as credentials produces noisy false positives, delays releases, and trains reviewers to ignore "this looks like an exposed secret" warnings — which is the opposite of what credential-leak detection should do. The trigger is "short alphanumeric AND value consumed by a teamvault function downstream"; real secrets are 100+ chars of PEM / base64 / hex.

## Reviewer guidance

**Do NOT flag as exposed credentials:**
- A 6-12 char alphanumeric value in an env file when the corresponding k8s manifest uses `teamvaultFileBase64` / `teamvaultPassword` / `teamvaultConfig`
- Env var names ending in `_KEY` that are short alphanumeric values
- The same short value appearing in dev.env + prod.env with different content (each cluster has its own teamvault namespace)

**DO flag:**
- A multi-line PEM literal in an env file (`-----BEGIN PRIVATE KEY-----...`)
- A 40+ char alphanumeric value not consumed by a teamvault function (likely a real token)
- A teamvault key checked into a public git repo for an unaffiliated organization (different cluster — leak risk)
- Missing `teamvaultXxx` wrapper on a secret yaml (raw substitution that would expose the lookup key, not the real secret, but still wrong)

## Anti-patterns

```yaml
# ❌ BAD — raw env substitution; the lookup key ends up in k8s Secret data
# instead of the real secret content
PEM_KEY: '{{ "WATCHER_X_PEM_KEY" | env }}'

# ❌ BAD — secret content checked into git
PEM_KEY: |
  -----BEGIN PRIVATE KEY-----
  MIIEvQIBADANBg...
  -----END PRIVATE KEY-----

# ✅ GOOD — teamvault function resolves the lookup key
PEM_KEY: '{{ "WATCHER_X_PEM_KEY" | env | teamvaultFileBase64 }}'
```

## Where the real secrets live

- Operator workstation: `~/.teamvault.json` (auth token for teamvault API)
- Build pipeline: `make buca` invokes `teamvault-config-parser` which streams the rendered yaml to `kubectl apply -f -` — the secret content exists in memory only for the duration of the apply
- Cluster: `Secret` resource at `<namespace>/<service-name>`; consumed by pods via `valueFrom.secretKeyRef`

The lookup key alone is useless to anyone without `~/.teamvault.json` + cluster apply privileges.

## Related

- `[[k8s-manifest-guide.md]]` — Secret manifest layout (`-secret.yaml` suffix, naming)
- `[[git-workflow.md]]` § "NEVER commit secrets" — applies to RAW secrets; teamvault keys are not secrets
- `[[go-k8s-binary-conventions.md]]` § "display:length on every secret field" — once a teamvault key is resolved at apply time, the pod sees the REAL secret in its env; the binary still must redact it from logs via `display:"length"`
