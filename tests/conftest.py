import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def long_article():
    return (
        "Scientists have discovered a potentially revolutionary method for carbon capture "
        "that could significantly accelerate efforts to combat climate change. The breakthrough "
        "involves engineered microorganisms that absorb CO2 at rates up to 20 times faster than "
        "natural processes. Researchers at MIT and Stanford collaborated on the project, publishing "
        "their findings in the journal Nature Climate Change. The organisms have been tested in "
        "controlled environments and show promise for deployment in industrial settings. If scaled "
        "successfully, the technology could capture billions of tons of carbon dioxide annually."
    )


@pytest.fixture
def short_text():
    return "Too short."
