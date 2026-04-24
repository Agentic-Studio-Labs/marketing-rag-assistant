# gcloud authentication (local + agent terminal)

Cursor and other tools run **`gcloud`** as **your macOS user**, using:

- `~/.config/gcloud/` — active account, project, named configurations  
- **Application Default Credentials (ADC)** — used by Terraform’s Google provider and Python `google-*` clients after `gcloud auth application-default login`

There is no separate “agent credential”; once your machine is logged in, **commands in this repo’s integrated terminal use the same auth**.

## 1. Check current state

```bash
gcloud auth list
gcloud config get-value account
gcloud config get-value project
gcloud auth application-default print-access-token >/dev/null && echo "ADC OK"
```

If **`ADC OK`** appears, Terraform and local tools that use ADC are already covered.

## 2. Log in (user credentials)

If you need to add or switch a Google account:

```bash
gcloud auth login
```

Complete the browser flow. Then pick the account CIH should use:

```bash
gcloud config set account YOUR_EMAIL@domain.com
```

## 3. Application Default Credentials (recommended for Terraform)

One-time (opens browser):

```bash
gcloud auth application-default login
```

Use the **same** Google identity that has access to the CIH GCP project (or one that can impersonate a deploy SA — see below).

## 4. Point gcloud at the CIH project

Production project for this app: **`content-intel-hub-prod`** (us-central1 Cloud Run: `cih-api-prod`, `cih-worker-prod`).

Your **default** project might be something other than CIH. Set it for this shell or use a **dedicated configuration** so you don’t overwrite other work.

**Option A — current config only**

```bash
gcloud config set project content-intel-hub-prod
```

**Option B — named configuration (recommended)**

```bash
gcloud config configurations create cih --no-activate   # skip if it already exists
gcloud config configurations activate cih
gcloud config set project content-intel-hub-prod
gcloud config set account YOUR_EMAIL@domain.com
```

Switch back to another project anytime:

```bash
gcloud config configurations list
gcloud config configurations activate default
```

## 5. Verify API access

```bash
gcloud services list --enabled --project=content-intel-hub-prod | head
gcloud run services list --region=us-central1 --project=content-intel-hub-prod
gcloud artifacts repositories list --location=us --project=content-intel-hub-prod
```

Fix **403** errors in IAM (e.g. **Editor** on the project, or narrower custom roles for deploy).

## 6. Optional: impersonate a service account

If your org prefers **no user keys** and uses a **deploy service account**:

```bash
gcloud auth application-default login --impersonate-service-account=deployer@content-intel-hub-prod.iam.gserviceaccount.com
```

Your user must have **`roles/iam.serviceAccountTokenCreator`** on that SA (or equivalent). This is often used with **least-privilege** deploy identities.

## 7. Do not commit secrets

- Never commit **JSON key files** or paste them into the repo.  
- Prefer **ADC** + user login or **impersonation** for local/Terraform use; in CI use **Workload Identity Federation**, not long-lived keys.

## After auth is correct

From repo root you can run deploy-related commands, for example:

```bash
gcloud config configurations activate cih   # if you use named config
gcloud builds submit --region=us-east1 ...
gcloud run deploy cih-worker ...
```

Exact deploy steps depend on your Artifact Registry region and service names; keep them in runbooks or CI, not in committed credentials.
