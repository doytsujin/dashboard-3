from functools import wraps
from unittest.mock import Mock, patch, mock_open


def patch_predictor():
    def test_method(func):
        @wraps(func)
        def inner_method(*args, **kwargs):
            with patch('rekcurd_dashboard.data_servers.LocalHandler.upload',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.LocalHandler.delete',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.CephHandler.download',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.CephHandler.upload',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.CephHandler.delete',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.AwsS3Handler.download',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.AwsS3Handler.upload',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.AwsS3Handler.delete',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.GcsHandler.download',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.GcsHandler.upload',
                          new=Mock(return_value=None)) as _, \
                    patch('rekcurd_dashboard.data_servers.GcsHandler.delete',
                          new=Mock(return_value=None)) as _, \
                    patch('builtins.open', new_callable=mock_open) as _:
                return func(*args, **kwargs)
        return inner_method
    return test_method
