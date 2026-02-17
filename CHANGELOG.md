# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.20] - 2026-02-17

### Added
- `-v`, `--version` flag to display version information and exit

### Changed
- Renamed `--version` parameter to `--project-version` for filtering by project version name
- Renamed `--project_group_name` parameter to `--project-group` for consistency with hyphenated naming
- Updated all documentation and examples with new parameter names

## [0.1.19] - 2026-02-17

### Added
- Comprehensive command-line parameter documentation to README with tables
- All 18 parameters organized into logical groups with descriptions and defaults

### Changed
- README now includes detailed parameter reference section

## [0.1.18] - 2026-02-17

### Fixed
- Fixed pyproject.toml license configuration to comply with PEP 639
- Removed deprecated "License :: OSI Approved :: MIT License" classifier

### Added
- Release automation script (release.ps1) for building and publishing packages
- Install automation script (install.ps1) for development and production installation
- Automatic version updating across all files during release

## [0.1.17] - 2026-02-16

### Added
- Initial package structure with modern Python packaging (pyproject.toml)
- Command-line entry points: `bd-metrics` and `blackduck-remediation-metrics`
- Module execution support: `python -m blackduck_remediation_metrics`
- New look and feel for reports
- Policy violations tracking and reporting
- Data visualization with charts
- Link to policy violation from policy name in reports
- Package-relative template path handling

### Changed
- Converted standalone script to proper Python package
- Updated template directory to use package resources
- Wrapped main execution in `main()` function for better modularity

### Fixed
- Template path now works correctly when installed as a package
- Database closing on exception handling improved

## Previous Versions (from original script)

### [0.1.16]
- Added link to policy violation from policy name in the report

### [0.1.15]
- Fixed issue where totalCount key was missing

### [0.1.14]
- Fixed issue where keyword snippetScanPresent was missing

### [0.1.13]
- Added missing remediation statuses UNDER_INVESTIGATION and AFFECTED

### [0.1.12]
- Fixed issues where there might be vulnerabilities without severity

### [0.1.11]
- Added NOT_AFFECTED remediation type
- Removed BetterJSONStorage usage

### [0.1.10]
- Added progressbar using tqdm to show progress of project analysis phases

### [0.1.9]
- Added feature to export report in JSON format by adding --json flag

### [0.1.8]
- Added check if project has updated compared to last run (project.updatedAt changed)
- Cache is updated if project info has changed

### [0.1.7]
- Changed to use BetterJSONStorage to improve performance and reduce database size

### [0.1.6]
- Added triangle icon in front of project version if last scanning date is older than threshold (--sinceDays, default 30 days)
- Added Last scanned date for project versions

### [0.1.5]
- Added usage of TinyDB (https://tinydb.readthedocs.io/) for caching BD metrics

## Unreleased

### Planned
- Enhanced error handling and validation
- Additional report formats
- Performance optimizations
- More comprehensive test coverage
- CI/CD pipeline integration
