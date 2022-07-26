import pytest
import mock
from zxcvbn import zxcvbn
from ckan.tests.helpers import call_action
from ckanext.oht.actions import user_create
import ckan.tests.factories as factories
from ckanext.oht.tests import get_context


DUMMY_PASSWORD = '01234567890123456789012345678901'


@pytest.fixture
def mock_token_urlsafe():
    with mock.patch('ckanext.oht.actions.secrets.token_urlsafe',
                    return_value=DUMMY_PASSWORD) as mock_token_urlsafe:
        yield mock_token_urlsafe


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestCreateUser():

    def test_unit_with_password(self, mock_token_urlsafe):
        next_action = mock.Mock()
        data_dict = {
            'name': 'test_user',
            'email': 'test@test.org',
            'password': 'password'
        }
        user_create(next_action, {}, data_dict)
        next_action.assert_called_once_with({}, data_dict)

    def test_unit_without_password(self, mock_token_urlsafe):
        next_action = mock.Mock()
        data_dict = {
            'name': 'test_user',
            'email': 'test@test.org'
        }
        user_create(next_action, {}, data_dict)
        expected_data_dict = {**data_dict, 'password': DUMMY_PASSWORD}
        next_action.assert_called_once_with({}, expected_data_dict)

    def test_auto_generated_password_is_strong(self):
        next_action = mock.Mock()
        data_dict = {
            'name': 'test_user',
            'email': 'test@test.org'
        }
        user_create(next_action, {}, data_dict)
        generated_password = next_action.call_args[0][1]['password']
        assert len(generated_password) > 30
        zxcvbn(generated_password)['score'] == 4

    def test_integration_without_password(self):
        call_action(
            'user_create',
            name='test_user',
            email='test@test.org'
        )
        sysadmin = factories.User(sysadmin=True)
        response = call_action(
            'user_show',
            get_context(sysadmin['name']),
            id='test_user',
            include_password_hash=True
        )
        assert response['password_hash']
