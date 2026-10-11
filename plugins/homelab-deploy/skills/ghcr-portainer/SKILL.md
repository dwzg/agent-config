---
name: ghcr-portainer
description: Set up or fix a GitHub Actions workflow that builds a Docker image, pushes it to GHCR and redeploys it through a Portainer webhook. Use when adding deployment to a self-hosted project, or when such a deploy fails with "manifest unknown", "unknown blob", a skipped webhook, or a commit that never deployed.
---

# Deploy to Portainer through GHCR

The pipeline: a push to `main` builds the image in GitHub Actions, pushes it to the GitHub container registry, and calls a Portainer stack webhook, which pulls the new image and restarts the container.

Start from [deploy.yml](deploy.yml) in this skill's directory. Copy it to `.github/workflows/deploy.yml` in the project, replace `IMAGE_NAME`, and keep every commented line unless you know why it is there. Each one exists because leaving it out broke a real deploy.

## The rules, and what breaks without each

1. **Push a plain manifest: `provenance: false` and `sbom: false`.** The buildx container driver attaches a provenance attestation by default. That turns the tag into an OCI index whose children are *untagged* package versions. An untagged-image cleanup job then deletes them. The tag still resolves, but every pull fails with `manifest unknown`.

2. **Clean up untagged versions *before* the push, never after.** Run last, the cleanup races the webhook for the image that was just pushed. Give it `continue-on-error: true`, so a cleanup problem never blocks a deploy.

3. **Use `docker/setup-buildx-action`.** The default `docker` driver can't export a build cache. With `cache-to: type=gha` and no buildx setup, the build fails before it starts on "Cache export is not supported for the docker driver". The webhook step is then skipped and the old image keeps serving, often with nothing on the pull request to show it.

4. **Tag `latest` *and* the commit SHA.** A bad deploy can then be rolled back by pinning the previous SHA in the compose file.

5. **Serialise deploys** with a `concurrency` group and `cancel-in-progress: false`. Two deploys racing leave whichever image finished last, which may not be the newest commit.

6. **A `GITHUB_TOKEN` push does not start another workflow.** If a scheduled job commits to `main` (a retrained model, generated data), the deploy will not run. Give `deploy.yml` a `workflow_dispatch` trigger and have that job call it explicitly.

7. **Pass the commit into the image** (`build-args: GIT_SHA=${{ github.sha }}`) and report it from a health endpoint. From outside, a stalled deploy and a fresh one look identical, and this is how to tell them apart.

8. **Workflow inputs go through `env:`, never into a `run:` body.** `${{ inputs.x }}` is substituted before the shell sees it, so a crafted value runs as shell on the runner.

## Secrets the workflow needs

| Secret | What it is |
| --- | --- |
| `PORTAINER_WEBHOOK_URL` | The stack's webhook URL from Portainer (stack → Webhooks). |
| `DELETE_PACKAGES_TOKEN` | A personal access token with `delete:packages`, for the cleanup step. |
| `GITHUB_TOKEN` | Provided automatically; needs `packages: write` in the job's `permissions`. |

## When it fails

- **`manifest unknown` on pull, tag still visible in GHCR:** rule 1. Rebuild with provenance off. The tag currently points at deleted children.
- **`ERROR: unknown blob` during push:** a transient registry error. Re-run the failed job once.
- **Workflow green, site unchanged:** check whether the webhook step ran (rule 3), whether Portainer's stack pulls `latest` with "re-pull image" enabled, and what commit the running container reports (rule 7).
- **A commit on `main` never deployed:** it was probably pushed by `GITHUB_TOKEN` (rule 6).

Since the deploy only runs after merge, add a separate CI workflow that runs the same `docker build` on pull requests, plus a smoke test of the started container. A broken Dockerfile then fails on the pull request, not on `main`.
