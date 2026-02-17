# Quick Start Guide

## Installation

### For Users

Install from source:

```bash
cd c:\Users\JouniLehto\repos\blackduck_remediation_metrics
pip install -e .
```

Or with development dependencies:

```bash
pip install -e .[dev]
```

### For Development

1. Clone the repository (already done)
2. Create a virtual environment (recommended):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install in development mode with all dependencies:

```bash
pip install -e .[dev,playwright]
```

4. Install Playwright browsers (for PDF generation with charts):

```bash
playwright install chromium
```

## Basic Usage

### Using the Command Line Tool

After installation, you can use the `bd-metrics` command:

```bash
bd-metrics --token="YOUR_ACCESS_TOKEN" --url="YOUR_BD_URL" --html --pdf
```

### Using as a Python Module

```bash
python -m blackduck_remediation_metrics --token="YOUR_ACCESS_TOKEN" --url="YOUR_BD_URL" --html
```

### Environment Variables

Set these to avoid passing token and URL each time:

```bash
$env:BD_TOKEN="YOUR_ACCESS_TOKEN"
$env:BD_URL="YOUR_BD_URL"

bd-metrics --html --pdf
```

## Common Commands

### Generate HTML report only

```bash
bd-metrics --html
```

### Generate interactive dashboard

```bash
bd-metrics --dashboard --json
```

### Use cache for better performance

```bash
bd-metrics --cache --html --pdf
```

### Filter by project

```bash
bd-metrics --project="MyProject" --version="1.0" --html
```

### Save reports to specific directory

```bash
bd-metrics --dir="./reports" --html --pdf
```

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=blackduck_remediation_metrics --cov-report=html
```

## Project Structure

```
blackduck-remediation-metrics/
├── src/
│   └── blackduck_remediation_metrics/
│       ├── __init__.py              # Package initialization
│       ├── __main__.py              # Module entry point
│       ├── blackduck_triage_extract.py  # Main script
│       └── templates/               # HTML templates
│           ├── BD_Results_Distribution_by_Triage_Status_v3.html
│           ├── BD_Results_Triage_Dashboard.html
│           └── style.css
├── tests/                           # Test files
├── pyproject.toml                   # Modern Python project config
├── setup.py                         # Setup script
├── requirements.txt                 # Dependencies
├── README.md                        # Full documentation
├── QUICKSTART.md                    # This file
└── LICENSE                          # MIT License
```

## Getting Help

View all available options:

```bash
bd-metrics --help
```

## Troubleshooting

### PDF Generation Issues

If PDFs are not generating correctly or charts are missing:

1. Install Playwright:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. Make sure wkhtmltopdf is installed: https://wkhtmltopdf.org/

### Import Errors

If you get import errors, make sure you installed the package:

```bash
pip install -e .
```

### Permission Errors

On Windows, you may need to run PowerShell as Administrator for some operations.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Review the [LICENSE](LICENSE) file for usage terms
