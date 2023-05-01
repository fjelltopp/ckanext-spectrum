import pytest
import ckan.plugins.toolkit as toolkit
from ckan.tests import factories


@pytest.mark.ckan_config('ckan.plugins', "spectrum scheming_datasets")
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestSysadminsOnlyCanAccessAPI():

    api_endpoints_to_test = [
        ('user_show'),
        ('package_list'),
        ('package_search'),
        ('user_list'),
        ('dataset_duplicate'),
        ('user_create')
    ]

    def test_unregistered_user_can_access_home(self, app):
        # Regression test: this feature was found to block access to homepage
        response = app.get('/')
        assert response.status_code == 200

    @pytest.mark.parametrize('action', api_endpoints_to_test)
    def test_api_endpoints_inaccessible_to_anonymous_users(self, app, action):
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function=action)
        )
        assert response.status_code == 403
        assert response.json == {
            'success': False,
            'error': {
                '__type': 'Not Authorized',
                'message': "Must be a system administrator."
            }
        }

    @pytest.mark.parametrize('action', api_endpoints_to_test)
    def test_api_endpoints_inaccessible_to_regular_users(self, app, action):
        user = factories.User(sysadmin=False)
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function=action),
            headers={
                'Authorization': user['apikey']
            }
        )
        assert response.status_code == 403
        assert response.json == {
            'success': False,
            'error': {
                '__type': 'Not Authorized',
                'message': "Must be a system administrator."
            }
        }

    @pytest.mark.parametrize('action', api_endpoints_to_test)
    def test_api_endpoints_accessible_to_sysadmin_users(self, app, action):
        user = factories.User(sysadmin=True)
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function=action),
            headers={
                'Authorization': user['apikey']
            }
        )
        assert response.status_code == 200


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestSubstituteUser():

    def test_error_raised_for_non_sysadmin_user(self, app):
        user = factories.User(sysadmin=False)
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function='package_list'),
            headers={
                'Authorization': user['apikey'],
                'CKAN-Substitute-User': 'fjelltopp_editor'
            }
        )
        assert response.status_code == 403

    def test_error_raised_for_invalid_substitute_user(self, app):
        user = factories.User(sysadmin=True)
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function='package_list'),
            headers={
                'Authorization': user['apikey'],
                'CKAN-Substitute-User': 'non_existant_user'
            }
        )
        assert response.status_code == 400
        assert response.json == {
            "success": False,
            "error": {
                "__type": "Bad Request",
                "message": "CKAN-Substitute-User header does "
                           "not identify a valid CKAN user"
            }
        }

    @pytest.mark.parametrize("user_field", ["id", "name"])
    def test_valid_substitute_user_request(self, app, user_field):
        sysadmin_user = factories.User(sysadmin=True)
        substitute_user = factories.User()
        dataset = factories.Dataset()
        dataset_create_url = toolkit.url_for(
            'api.action',
            ver=3,
            logic_function='package_create',
            id=dataset['id']
        )
        response = app.post(
            dataset_create_url,
            json={'name': 'test-dataset'},
            headers={
                'Authorization': sysadmin_user['apikey'],
                'CKAN-Substitute-User': substitute_user[user_field]
            }
        )
        assert response.status_code == 200
        assert response.json['result']['creator_user_id'] == substitute_user['id']
