from unittest.mock import patch, Mock

from drucker_dashboard.protobuf import drucker_pb2
from .base import BaseTestCase, create_app_obj, create_service_obj, create_eval_obj, create_eval_result_obj
from io import BytesIO
from drucker_dashboard.models import EvaluationResult, Evaluation


class ApiEvaluationTest(BaseTestCase):
    """Tests for ApiEvaluation.
    """

    @patch('drucker_dashboard.drucker_dashboard_client.drucker_pb2_grpc.DruckerDashboardStub')
    def test_post(self, mock_stub_class):
        mock_stub_obj = Mock()
        mock_stub_obj.UploadEvaluationData.return_value = drucker_pb2.UploadEvaluationDataResponse(status=1, message='success')
        mock_stub_class.return_value = mock_stub_obj
        aobj = create_app_obj()
        create_service_obj(aobj.application_id)

        url = f'/api/applications/{aobj.application_id}/evaluation'
        content_type = 'multipart/form-data'
        file_content = b'my file contents'
        response = self.client.post(url,
                                    content_type=content_type,
                                    data={'file': (BytesIO(file_content), "file.txt")})
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json, {'status': True, 'evaluation_id': 1})

        # duplication check
        response = self.client.post(url,
                                    content_type=content_type,
                                    data={'file': (BytesIO(file_content), "file.txt")})
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json, {'status': True, 'evaluation_id': 1})

    def test_delete(self):
        app_id = create_app_obj().application_id
        eobj = create_eval_obj(app_id, save=True)
        sobj = create_service_obj(app_id)
        create_eval_result_obj(model_id=sobj.model_id, evaluation_id=eobj.evaluation_id, save=True)
        response = self.client.delete(f'/api/applications/{app_id}/evaluation/{eobj.evaluation_id}')
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.json, {'status': True, 'message': 'Success.'})
        self.assertEqual(Evaluation.query.all(), [])
        self.assertEqual(EvaluationResult.query.all(), [])

        response = self.client.delete(f'/api/applications/{app_id}/evaluation/101')
        self.assertEqual(404, response.status_code)
        self.assertEqual(response.json, {'status': False})
