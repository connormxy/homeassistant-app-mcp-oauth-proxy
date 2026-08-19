---
description: Automatically increments the `-dev.X` tag in add-on `config.yaml` versions to trigger GitHub Actions remote multi-arch container builds for local Home Assistant OS testing.
---

# Bump Dev Version

**Description**: Automatically increments the `-dev.X` tag in add-on `config.yaml` versions to trigger GitHub Actions remote multi-arch container builds for local Home Assistant OS testing.

## Prerequisites

- You must be on the `dev` branch.
- Your Home Assistant repository must be using standard `-dev.X` trailing tags for versions.

## Workflow Execution Steps

When you need to publish changes for testing on Home Assistant OS:

```bash
python scratch/bump_dev.py && git commit -am "chore: bump dev version" && git push origin dev
```

### Breakdown of Pipeline

- `python scratch/bump_dev.py`: Parses all add-on `config.yaml` files and increments the `-dev.X` version string.
- `git commit -am "..."`: Commits the version bump.
- `git push origin dev`: Pushes to GitHub to trigger the `.github/workflows/builder.yaml` multi-arch GHCR build action.
