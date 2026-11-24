# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-tuya-ipc-p2p/issues/new/choose)
with:

- the Home Assistant version, the integration version and the camera model;
- what you did, what you expected and what happened;
- the diagnostics downloaded from the integration's menu (the account and the
  camera keys are redacted) and the debug log of the problem.

## Where the code lives

The Tuya protocol (sign-in, signaling, relay, decryption and motion detection)
lives in the companion library
[tuya-ipc-p2p-sdk](https://github.com/roquerodrigo/tuya-ipc-p2p-sdk). This
repository holds the Home Assistant side: the config flow, the entities and
their lifecycle. A fix in the protocol is released in the library first, then
brought here by a pull request that bumps the pinned version in
`manifest.json` and `pyproject.toml` together.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/).

```bash
scripts/setup      # install the dependencies into .venv
scripts/develop    # run Home Assistant at http://localhost:8123 with this integration loaded
```

`scripts/develop` uses the configuration in [`config/`](config/), with debug
logging on for the integration.

## Checks

Run these before opening a pull request. CI runs the same ones, and
`pre-commit install` runs the first three on every commit.

```bash
uv run ruff format .                         # format
uv run ruff check . --fix                    # lint
uv run mypy custom_components/tuya_ipc_p2p   # type-check
uv run pytest                                # tests, coverage must stay at 90 % or more
```

`scripts/lint` runs the same four checks without changing any file, as CI
does.

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/).
   Releases and their notes are generated from them. Mark breaking changes
   with `!` or a `BREAKING CHANGE:` footer.
3. Update `translations/en.json` and `translations/pt-BR.json` together when
   you change user-facing strings. The tests fail if their keys differ.
4. Update the README when behaviour, configuration or entities change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
