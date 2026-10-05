# Changelog

All notable changes to Loot Scaler. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.2] - 2026-10-05

### Fixed
- The mod declared itself compatible with Minecraft 1.21 and newer, but it
  is built against the unobfuscated names of 26.2 and crashes on older
  versions. It now requires Minecraft 26.2 or newer.

## [1.0.1] - 2026-09-23

### Changed
- Java package is now `io.github.dschonas04.lootscaler`, matching the
  GitHub handle.

### Removed
- The Python data pack generator. Loot Scaler is a Fabric mod only.

## [1.0.0] - 2026-09-23

### Added
- Fabric mod that scales ore and mob drops from
  `config/loot-scaler.properties` (`ores`, `mobs`, `never_zero`, `debug`).
- Amounts are scaled, never drop chances: a single ore always gives its
  item, only the Fortune bonus and multi-item drops shrink.
- Works for modded ores and mobs without a list of loot tables, through one
  mixin on `LootPool#addRandomItems`.

[Unreleased]: https://github.com/Dschonas04/loot-scaler/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/Dschonas04/loot-scaler/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/Dschonas04/loot-scaler/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Dschonas04/loot-scaler/releases/tag/v1.0.0
