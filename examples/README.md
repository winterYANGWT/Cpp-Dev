# Examples

The examples directory contains small downstream projects that exercise the
template's public package contract.

## `universe_answer`

`examples/universe_answer` is a minimal installed-package consumer. It builds a
single `universe_answer_cli` executable that links the installed
`{project_name}::{project_name}` target, calls `{project_name}::Answer()`, and
prints:

```text
The answer to life, the universe, and everything is 42.
```

Build it from an installed tree:

```sh
cmake --preset quality
cmake --build --preset quality
cmake --install build/quality --prefix build/install
cmake -S examples/universe_answer -B build/examples/universe_answer -DCMAKE_PREFIX_PATH="$PWD/build/install"
cmake --build build/examples/universe_answer
ctest --test-dir build/examples/universe_answer --output-on-failure
```

The standard quality gate also runs this installed-package consumer check:

```sh
python3 scripts/quality.py check
```
