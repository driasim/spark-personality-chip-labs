# Security Policy

Spark Personality Chip Labs is a local-first personality chip repo. The repo
should not contain runtime secrets or private user state.

## Do Not Commit

- `.env` files
- provider API keys
- Telegram bot tokens
- private transcripts
- private memory exports
- generated runtime state from `~/.spark`
- private customer/user personality notes
- voice provider ids that identify a private paid voice

## Safe Public Content

- schema definitions
- example personality YAML files
- loader and hook code
- tests with fake data
- docs and validation scripts

## Local Runtime State

The active personality resolver may read:

- `SPARK_PERSONALITY`
- `~/.spark/active_personality.json`
- a project-local `.personality` file

Those files are operator/user state. They should not be treated as public repo
content and should not be copied into examples unless the values are fake.

## Before Making A Fork Public

Run a secret scan across tracked files and working-tree files. Also inspect git
history if the repo was ever private.

Suggested checks:

```bash
git grep -n -I -E "<your-secret-patterns>" HEAD -- .
rg -n --hidden --glob '!**/.git/**' "<your-secret-patterns>" .
python -m pytest -q
```

If history contains real credentials, rotate the credential and publish from a
scrubbed repo or rewritten history.
