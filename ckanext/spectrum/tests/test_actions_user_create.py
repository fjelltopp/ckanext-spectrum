import mock
import pytest
from zxcvbn import zxcvbn

import ckan.tests.factories as factories
from ckan.tests.helpers import call_action
from ckanext.spectrum.actions import user_create
from ckanext.spectrum.tests import get_context

DUMMY_PASSWORD = '01234567890123456789012345678901'
DUMMY_USERNAME = 'dummy-123'


@pytest.fixture
def mock_token_urlsafe():
    with mock.patch('ckanext.spectrum.actions.secrets.token_urlsafe',
                    return_value=DUMMY_PASSWORD) as mock_token_urlsafe:
        yield mock_token_urlsafe


@pytest.fixture
def mock_random_username():
    with mock.patch('ckanext.spectrum.actions._get_random_username_from_email',
                    return_value=DUMMY_USERNAME) as mock_random_username:
        yield mock_random_username


@pytest.fixture
def spectrum_org():
    return factories.Organization(name="spectrum")


@pytest.mark.ckan_config('ckan.plugins', "spectrum")
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestCreateUser():

    def test_unit_without_autogeneration(self, mock_token_urlsafe):
        user = factories.User()
        next_action = mock.Mock(return_value=user)
        ctx = {'user': user}
        data_dict = {
            'name': 'test_user',
            'email': 'test@test.org',
            'password': 'password'
        }
        user_create(next_action, ctx, data_dict)
        next_action.assert_called_once_with(ctx, data_dict)

    def test_unit_with_autogeneration(self, mock_token_urlsafe, mock_random_username):
        user = factories.User()
        next_action = mock.Mock(return_value=user)
        data_dict = {
            'email': 'test@test.org'
        }
        context = get_context(user)
        user_create(next_action, context, data_dict)
        expected_data_dict = {
            **data_dict,
            'password': DUMMY_PASSWORD,
            'name': DUMMY_USERNAME
        }
        next_action.assert_called_once_with(context, expected_data_dict)

    def test_auto_generated_password_is_strong(self):
        user = factories.User()
        next_action = mock.Mock(return_value=user)
        ctx = {'user': user}
        data_dict = {
            'name': 'test_user',
            'email': 'test@test.org'
        }
        user_create(next_action, ctx, data_dict)
        generated_password = next_action.call_args[0][1]['password']
        assert len(generated_password) > 30
        assert zxcvbn(generated_password)['score'] == 4

    def test_new_user_can_create_datasets(self, spectrum_org):
        user = call_action(
            'user_create',
            email='test@test.org'
        )
        user_orgs = call_action('organization_list_for_user', id=user['id'], permission='create_dataset')
        assert len(user_orgs) == 1
        assert spectrum_org["name"] in [org["name"] for org in user_orgs]

    def test_user_create_works_if_no_spectrum_org_present(self):
        user = call_action(
            'user_create',
            email='test@test.org'
        )
        assert user['email'] == 'test@test.org'

    def test_integration(self, spectrum_org):
        response = call_action(
            'user_create',
            email='test@test.org'
        )
        sysadmin = factories.User(sysadmin=True)
        response = call_action(
            'user_show',
            get_context(sysadmin['name']),
            id=response['name'],
            include_password_hash=True
        )
        assert response['password_hash']


