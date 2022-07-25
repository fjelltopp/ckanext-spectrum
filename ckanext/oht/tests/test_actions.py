import pytest
import mock
from ckan.tests.helpers import call_action


@pytest.fixture
def mock_encrypt():
    dummy_hashed_password = (
        '$pbkdf2-sha512$25000$ZsyZs1bqfe.d07qXsvZeyw$G7VBEvwdL'
        'rzhZB0/8/w89XvzXDCF1PPcz7agyExrQnBKbbFN9qK8Z6OH0eNhUc'
        'a2yHfowYbYQyBV5lAe0PcNBg'
    )
    with mock.patch('ckan.model.user.pbkdf2_sha512.encrypt',
                    return_value=dummy_hashed_password) as mock_encrypt:
        yield mock_encrypt


@pytest.fixture
def mock_token_urlsafe():
    dummy_token = '01234567890123456789012345678901'
    with mock.patch('ckanext.oht.actions.secrets.token_urlsafe',
                    return_value=dummy_token) as mock_token_urlsafe:
        yield mock_token_urlsafe


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestCreateUser():

    def test_with_password(self, mock_encrypt, mock_token_urlsafe):
        call_action(
            'user_create',
            name='test_user',
            email='test@test.org',
            password='password'
        )
        mock_token_urlsafe.assert_not_called()
        mock_encrypt.assert_called_once_with('password')

    def test_with_no_password(self, mock_encrypt, mock_token_urlsafe):
        call_action(
            'user_create',
            name='test_user',
            email='test@test.org'
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_encrypt.assert_called_once_with('01234567890123456789012345678901')
