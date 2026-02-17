"""Basic tests for the blackduck_remediation_metrics package."""
import pytest
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blackduck_remediation_metrics import __version__, __author__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.17"


def test_author():
    """Test that author is defined."""
    assert __author__ == "Jouni Lehto"


def test_templates_exist():
    """Test that template files exist in the package."""
    from blackduck_remediation_metrics import blackduck_triage_extract
    templates_dir = Path(blackduck_triage_extract.__file__).parent / "templates"
    assert templates_dir.exists()
    assert (templates_dir / "BD_Results_Distribution_by_Triage_Status_v3.html").exists()
    assert (templates_dir / "BD_Results_Triage_Dashboard.html").exists()


def test_import():
    """Test that the main module can be imported."""
    from blackduck_remediation_metrics import main
    assert callable(main)
