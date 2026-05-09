# Release Checklist

Pre-flight before publishing a new version to PyPI.

## 1. Confirm the work is mergeable

- [ ] `main` is ahead of the previous release tag
- [ ] All CI / test suites pass
- [ ] No pending migrations: `nautobot-server makemigrations --check --dry-run nautobot_contract_models`
- [ ] Lint clean: `uvx ruff check src/ tests/ && uvx ruff format --check src/ tests/`
- [ ] Browser-verified any new UI surface

## 2. Bump the version

This plugin uses [CalVer](https://calver.org/). The version is `YYYY.M.D` (e.g. `2026.5.9`). Same-day post-releases use a `.N` suffix.

Update in `pyproject.toml`:

```toml
[project]
version = "YYYY.M.D"
```

Update in `src/nautobot_contract_models/__init__.py` if `__version__` is set there.

## 3. Update PLAN.md and the release notes

- [ ] PLAN.md — mark phases DONE, add any new phase entries
- [ ] `docs/admin/release_notes/version_<X>.md` — write the release note
- [ ] `docs/admin/release_notes/index.md` — add a row for the new version
- [ ] `mkdocs.yml` — add the new release note to the nav

## 4. PII audit before publishing

**This is non-negotiable.** Per `~/.claude/rules/python.md`:

```shell
rm -rf dist/ /tmp/sdist-audit
uv build
mkdir -p /tmp/sdist-audit
tar -xzf dist/*.tar.gz -C /tmp/sdist-audit

# Scan for anything that shouldn't ship to PyPI
grep -rnEi 'real-domain-pattern|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|customer-name|/home/' /tmp/sdist-audit/
```

The expected output is **empty**. Anything else means scrub the source, rebuild, re-audit. The sdist's blast surface is larger than just `src/`: hatchling pulls in `docs/`, top-level dotfiles, `uv.lock`, and `CHANGELOG.md` — the curated grep across just `src/` would miss them.

## 5. Publish

```shell
uv publish --token $(grep password ~/.pypirc | head -1 | awk '{print $3}')
```

Note: `uv publish` does NOT read `~/.pypirc`; the token has to be passed explicitly.

`uv publish` does not abort mid-upload. Once the HTTP request is in flight, killing the local process does NOT recall the file from PyPI. Treat any `uv publish` invocation as committed.

## 6. Verify

```shell
pip index versions nautobot-contract-models
# Should show the new version
```

Wait ~2 minutes for PyPI to propagate, then:

```shell
pip install --upgrade nautobot-contract-models
pip show nautobot-contract-models
# Confirm version matches
```

## 7. Tag the release

```shell
git tag YYYY.M.D
git push origin YYYY.M.D
```

## 8. If you leak something

1. **Yank immediately**: PyPI web UI → `https://pypi.org/manage/project/nautobot-contract-models/release/<version>/` → Options → Yank. Yanking marks the version "do not install" but doesn't delete the file.
2. **Email PyPI security** for genuine PII leaks: `admin@pypi.org`. They sometimes do full deletion. Days, not minutes.
3. **Publish a post-release** with sanitized content: bump `version = "YYYY.M.D.1"` and re-run the checklist.
