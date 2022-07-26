import pytest
import ckan.plugins.toolkit as toolkit
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
class TestSysadminsOnlyCanAccessAPI():

    def test_error_raised_for_unregistered_user(self, app):
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function='package_list')
        )
        assert response.status_code == 403
        assert response.json == {
            'success': False,
            'error': {
                '__type': 'Not Authorized',
                'message': "Must be a system administrator to perform this action."
            }
        }

    def test_error_raised_for_non_sysadmin_user(self, app):
        user = factories.User(sysadmin=False)
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function='package_list'),
            headers={
                'Authorization': user['apikey']
            }
        )
        assert response.status_code == 403
        assert response.json == {
            'success': False,
            'error': {
                '__type': 'Not Authorized',
                'message': "Must be a system administrator to perform this action."
            }
        }


@pytest.mark.usefixtures("clean_db")
class TestSubstituteUser():

    def test_error_raised_for_unregistered_user(self, app):
        response = app.get(
            toolkit.url_for('api.action', ver=3, logic_function='package_list'),
            headers={'CKAN-Substitute-User': 'fjelltopp_editor'}
        )
        assert response.status_code == 403

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

    def test_valid_substitute_user_request(self, app):
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
                'CKAN-Substitute-User': substitute_user['name']
            }
        )
        assert response.status_code == 200
        assert response.json['result']['creator_user_id'] == substitute_user['id']
