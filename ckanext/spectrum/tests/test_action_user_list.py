import pytest
import ckan.tests.factories as factories
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config('ckan.plugins', "spectrum")
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestListUsers():

    def test_empty_query(self):
        users = [factories.User(name=f"{i}01dec4a-6cc9-49cd-91ea-cc0e09ba620d") for i in range(3)]
        response = call_action(
            'user_list',
            q=''
        )
        user_ids_created = {u['id'] for u in users}
        user_ids_found = {u['id'] for u in response}
        assert user_ids_created == user_ids_found

    def test_search_by_id(self):
        users = [factories.User(name=f"{i}01dec4a-6cc9-49cd-91ea-cc0e09ba620d") for i in range(3)]
        response = call_action(
            'user_list',
            q=users[1]['id']
        )
        user_ids_found = [u['id'] for u in response]
        assert user_ids_found == [users[1]['id']]

    def test_search_by_non_id(self):
        users = [factories.User(name=f"{i}01dec4a-6cc9-49cd-91ea-cc0e09ba620d") for i in range(3)]
        response = call_action(
            'user_list',
            q=users[2]['name']
        )
        user_ids_found = [u['id'] for u in response]
        assert user_ids_found == [users[2]['id']]
