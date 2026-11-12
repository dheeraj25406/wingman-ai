import os
import sys

# Ensure test environment settings
os.environ.setdefault("ENVIRONMENT", "test")
if "ADMIN_API_KEY" not in os.environ or os.environ.get("ADMIN_API_KEY") == "your_admin_secret_key_here":
    os.environ["ADMIN_API_KEY"] = ""

# Ensure test database isolation: divert from production /wingman to /wingman_test
db_url = os.environ.get("DATABASE_URL", "")
if db_url and db_url.endswith("/wingman"):
    os.environ["DATABASE_URL"] = db_url[:-8] + "/wingman_test"

# Synchronize backend settings if already loaded
try:
    from backend.app.core.config import settings
    if settings.ADMIN_API_KEY == "your_admin_secret_key_here":
        settings.ADMIN_API_KEY = ""
    settings.ENVIRONMENT = "test"
except ImportError:
    pass

