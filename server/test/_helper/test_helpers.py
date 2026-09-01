import configparser
import os.path
import urllib.error
import urllib.request

TEST_CONFIG = configparser.ConfigParser()
TEST_CONFIG.read(
    (
        os.path.join(os.path.dirname(__file__), "..", "test_config.default.ini"),
        os.path.join(os.path.dirname(__file__), "..", "test_config.ini"),
    )
)


# Check if the server is available. Otherwise, skip tests.
try:
    urllib.request.urlopen(TEST_CONFIG["server"]["url"] + "/description", timeout=2)
    SERVER_OKAY = True
    SERVER_ERROR = None
except urllib.error.URLError as e:
    SERVER_OKAY = False
    SERVER_ERROR = e
