# Black Duck Remediation Metrics

A Python module for extracting and analyzing remediation status metrics from Black Duck.

## Description

This script is used to export remediation status for a given level. By default, the script exports the status for all projects in a given Black Duck instance. There are filtering options implemented to limit the project count.

## Features

- Export remediation status for all projects in a Black Duck instance
- Filter by project groups (including recursive sub-groups)
- Filter by specific projects and versions
- Filter by phase categories (PLANNING, DEVELOPMENT, RELEASED, DEPRECATED, ARCHIVED, PRERELEASE)
- Filter by distribution categories (EXTERNAL, SAAS, INTERNAL, OPENSOURCE)
- Generate HTML, PDF, and JSON reports
- Generate interactive dashboards with charts and visualizations
- Cache support for improved performance
- Progress tracking with progress bars

## Installation

### From PyPI (when published)

```bash
pip install blackduck-remediation-metrics
```

### From source

```bash
git clone https://github.com/jounilehto/blackduck-remediation-metrics.git
cd blackduck-remediation-metrics
pip install -e .[dev]
```

### Requirements

- Python 3.8 or higher
- wkhtmltopdf (for PDF generation) - Download from https://wkhtmltopdf.org/

### Optional Dependencies

For enhanced dashboard features with Playwright:

```bash
pip install blackduck-remediation-metrics[playwright]
playwright install
```

## Usage

### Getting an Access Token

To get an Access Token, use your Internet browser and go to:
```
<BD_URL>/api/current-user/tokens?limit=100&offset=0
```

Click "+ Create Token", give it a name and Scope: "Read and Write Access", then click "Create". Copy and paste the given access token.

**NOTE:** After you click "Close", you cannot see the token anymore.

### Command Line Interface

#### Generate HTML and PDF reports for all projects

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --html --pdf --json
```

#### Generate interactive dashboard

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --dashboard --json
```

#### Use cache for improved performance

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --cache --html --pdf --json
```

#### Filter by project group

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --project_group_name="<PROJECT_GROUP_NAME>" --html --pdf
```

#### Filter by specific project and version

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --project="<PROJECT_NAME>" --version="<PROJECT_VERSION_NAME>" --html --pdf
```

#### Filter by phase categories

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --phaseCategories="PLANNING,DEVELOPMENT" --html --pdf
```

#### Filter by distribution categories

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --distributionCategories="EXTERNAL" --html
```

#### Specify output directory

```bash
bd-metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --dir="./reports" --html --pdf
```

## Command-Line Parameters

### Required Parameters

| Parameter | Description | Environment Variable |
|-----------|-------------|---------------------|
| `--url` | Base URL for Black Duck Hub | `BD_URL` |
| `--token` | Black Duck access token | `BD_TOKEN` |

**Note:** Both parameters can be set via environment variables instead of command-line arguments.

### Project/Version Filtering

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--project` | Filter by specific Black Duck project name | None (all projects) |
| `--version` | Filter by specific project version name (requires `--project`) | None (all versions) |
| `--project_group_name` | Filter by project group name (includes sub-groups recursively) | None |

### Phase and Distribution Filtering

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `--phaseCategories` | Comma-separated list of version phases to include | All phases | `PLANNING`, `DEVELOPMENT`, `RELEASED`, `DEPRECATED`, `ARCHIVED`, `PRERELEASE` |
| `--distributionCategories` | Comma-separated list of version distributions to include | All distributions | `EXTERNAL`, `SAAS`, `INTERNAL`, `OPENSOURCE` |

### Report Generation Options

| Parameter | Description | Type |
|-----------|-------------|------|
| `--html` | Generate HTML report | Flag |
| `--pdf` | Generate PDF report (requires wkhtmltopdf) | Flag |
| `--json` | Generate JSON report | Flag |
| `--csv` | Generate CSV report | Flag |
| `--dashboard` | Generate interactive dashboard HTML report with charts | Flag |

**Note:** You can specify multiple report types in a single run.

### Cache and Database Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--cache` | Use TinyDB as a cache for improved performance on subsequent runs | Disabled |
| `--db_file` | TinyDB database file path | `bd_remediation_db.json` |
| `--cache_truncate` | Clean/truncate the cache file before running | Disabled |

### Output and Logging Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--dir` | Output directory for generated reports | `.` (current directory) |
| `--log_level` | Logging level for console output | `INFO` |
| `--sinceDays` | Number of days to mark project versions as dormant (shows warning icon) | `30` |

### Environment Variables

You can set token and URL parameters as environment variables:

```bash
export BD_TOKEN="<BD_TOKEN>"
export BD_URL="<BD_URL>"
```

Then run without --token and --url arguments:

```bash
bd-metrics --html --pdf
```

### Proxy Configuration

If a proxy is needed, use the export method:

```bash
export HTTP_PROXY='http://10.10.10.10:8000'
export HTTPS_PROXY='https://10.10.10.10:1212'
```

### Using as a Python Module

```python
from blackduck_remediation_metrics import main

# Call the main function (sys.argv will be used for arguments)
main()
```

Or run as a module:

```bash
python -m blackduck_remediation_metrics --token="<ACCESS_TOKEN>" --url="<BD_URL>" --html
```

## Project Structure

```
blackduck-remediation-metrics/
├── src/
│   └── blackduck_remediation_metrics/
│       ├── __init__.py
│       ├── __main__.py
│       ├── blackduck_triage_extract.py
│       └── templates/
│           ├── BD_Results_Distribution_by_Triage_Status_v3.html
│           └── BD_Results_Triage_Dashboard.html
├── tests/
├── pyproject.toml
├── requirements.txt
├── setup.py
├── README.md
└── LICENSE
```

## Version History

- 0.1.19 - Added comprehensive command-line parameter documentation to README
- 0.1.18 - Fixed pyproject.toml license configuration for PEP 639 compliance
- 0.1.17 - Added new look and feel, added policy violations, added data visualization
- 0.1.16 - Added link to policy violation from policy name in the report
- 0.1.15 - Fixed issue where totalCount key was missing
- 0.1.14 - Fixed issue where key word snippetScanPresent was missing
- 0.1.13 - Added missing remediation statuses UNDER_INVESTIGATION and AFFECTED
- 0.1.12 - Fixed issues where there might be vulnerabilities without severity
- 0.1.11 - Added NOT_AFFECTED remediation type and removed BetterJSONStorage usage
- 0.1.10 - Added progressbar using tqdm to show progress of project analysis phases
- 0.1.9 - Added feature to export report in JSON format
- 0.1.8 - Added check if project has updated compared to last run
- 0.1.7 - Changed to use BetterJSONStorage to improve performance and reduce database size
- 0.1.6 - Added triangle icon and last scanned date for project versions
- 0.1.5 - Added usage of TinyDB for caching BD metrics

## License

MIT License

## Author

Jouni Lehto

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the GitHub issue tracker.
