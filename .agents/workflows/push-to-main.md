---
description: Automates the process of graduating experimental `dev` changes into stable production releases on the `main` branch, ensuring all `(DEV)` branding, slugs, URLs, and experimental tags are stripped out before publishing.
---

# Publish to Main (Release Pipeline)

**Description**: Automates the process of graduating experimental `dev` changes into stable production releases on the `main` branch, ensuring all `(DEV)` branding, slugs, URLs, and experimental tags are stripped out before publishing. It also automatically triggers the GitHub Actions pipeline to pre-build the production multi-arch Docker images.

## Prerequisites

- All active work must be fully committed and pushed to the `dev` branch.
- The `scratch/publish_to_main.py` cleanup script must exist and be functional.

## Workflow Execution Steps

When requested to push changes to main or release a new stable version, run the following pipeline:

```bash
git checkout main && git merge dev && python scratch/publish_to_main.py && git commit -am 'chore: prepare release' && git push origin main && git checkout dev
```

### Breakdown of Pipeline

- `git checkout main`: Switches to the production branch.
- `git merge dev`: Merges the dev changes (clean ancestor tree, zero history issues).
- `python scratch/publish_to_main.py`: Executes the cleanup script that removes `(DEV)` names, experimental stages, `#dev` branch URL suffixes, and updates `image: ...-dev` to `image: ...`.
- `git commit -am 'chore: prepare release'`: Commits the cleaned production files.
- `git push origin main`: Pushes the stable release up to GitHub. **This triggers `.github/workflows/builder.yaml` to build and publish the production `latest` multi-arch Docker images.**
- `git checkout dev`: Drops you back into the development environment to continue working.
