# prompt-regression

[![PyPI version](https://img.shields.io/pypi/v/trysac-prompt-regression)](https://pypi.org/project/trysac-prompt-regression/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-prompt-regression)](LICENSE)
[![CI](https://github.com/Trysac/u033-prompt-regression/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u033-prompt-regression/actions/workflows/ci.yml)

Compare recorded outputs of two prompt versions over the same dataset and report unchanged, changed, improved, regressed, added and removed cases

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-prompt-regression
# or
uv add trysac-prompt-regression
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import prompt_regression

# normalize() trims surrounding whitespace and lower-cases the text.
print(prompt_regression.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    prompt_regression.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
