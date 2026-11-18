# Release the Python SDK

Releases are published by `.github/workflows/release.yml` when a stable version tag is pushed. Run the commands below from this SDK repository root.

## Registry setup

In PyPI, configure a GitHub Trusted Publisher for project `vortexify`, owner `vortexifyai`, repository `python-sdk`, and workflow `release.yml`. Leave the environment field blank.

GitHub Actions must be enabled. Publishing uses GitHub OIDC; no registry token secret or interactive login is needed. The workflow does not specify a GitHub environment, matching the blank environment field in the trusted publisher.

## Publish a version

Update `[project].version` in `pyproject.toml` and add the matching `### vVERSION` entry to the README changelog.

Commit those files with the source changes, merge and push them to `main`, then tag that commit. For the prepared release:

```sh
git tag v0.1.2
git push origin v0.1.2
```

The workflow installs the SDK and test dependencies, runs the full test suite, builds a wheel and source archive, and checks them with Twine. The tag must match the committed package version and changelog. A separate job publishes the built files to PyPI. After publication, another job creates a GitHub Release containing those same files and generated release notes.

Watch the run in **Actions** and verify `vortexify` on PyPI after it completes. Versions and changelogs are committed before release; the workflow does not push commits back or use the parent repository's release JSON files.

## Check locally without publishing

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]' build twine
python -m pytest
python -m build
python -m twine check dist/*
```

## Retry a failed release

A failure before publication can be retried after resolving its cause. If PyPI accepted the upload and only the GitHub Release job failed, rerun only that failed job. Do not move a published tag or reuse its package version for changed contents; publish a new version instead.
