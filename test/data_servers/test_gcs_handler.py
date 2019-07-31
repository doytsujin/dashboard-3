import unittest

from rekcurd_dashboard.models import DataServerModel, DataServerModeEnum
from rekcurd_dashboard.data_servers import GcsHandler

from . import patch_predictor


class GcsHandlerTest(unittest.TestCase):
    """Tests for GcsHandlerTest.
    """

    def setUp(self):
        self.data_server_model = DataServerModel(
            project_id=1, data_server_mode=DataServerModeEnum.GCS,
            gcs_access_key="xxx", gcs_secret_key="xxx", gcs_bucket_name="xxx")
        self.handler = GcsHandler()

    @patch_predictor()
    def test_download(self):
        self.assertIsNone(self.handler.download(self.data_server_model, "remote", "local"))

    @patch_predictor()
    def test_upload(self):
        self.assertIsNone(self.handler.upload(self.data_server_model, "remote", "local"))
