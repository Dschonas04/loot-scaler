# Contributing

Thanks for wanting to improve Loot Scaler.

## Reporting bugs

Open an [issue](https://github.com/Dschonas04/loot-scaler/issues/new/choose) with
the mod, Minecraft and Fabric Loader versions and the relevant part of
`logs/latest.log`.

## Building

Minecraft 26.2 ships without obfuscation, so the mod builds with plain Gradle
against the server jar, without Loom or mappings. You need Java 25 and Gradle.

```bash
tools/fetch-libs.sh   # server jar from Mojang into libs/
gradle build          # jar in build/libs/
```

`libs/` is ignored by git: the Minecraft jar must not be redistributed.

## Pull requests

1. Fork, create a branch, make the change.
2. `gradle build` must pass; please try it in game as well.
3. Add a line under "Unreleased" in [CHANGELOG.md](CHANGELOG.md).
4. Open a pull request and say what changes and why.

## Releases

Bump `mod_version` in `gradle.properties`, move the "Unreleased" notes to a
new version in CHANGELOG.md, tag `v<version>` and push the tag. The build
workflow publishes the release with the jar.

## License

By contributing you agree that your work is released under the
[MIT License](LICENSE).
