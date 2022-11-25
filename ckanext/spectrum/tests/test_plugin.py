import pytest

from ckan.tests import factories
from ckan.tests.helpers import call_action
from ckanext.spectrum.tests import get_context


@pytest.mark.ckan_config('ckan.plugins', "spectrum scheming_datasets")
@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestPrivateDatasetActivities():

    def test_activity_is_created_when_creating_private_dataset(self):
        user = factories.User()
        result = call_action(
            'package_create',
            get_context(user['name']),
            name="updated-name",
            private=True,
            owner_org=factories.Organization()['id']
        )
        activity_stream = call_action(
            'package_activity_list',
            get_context(user['name']),
            id=result['id']
        )
        assert len(activity_stream) == 1

    def test_activity_is_created_when_updating_private_dataset(self):
        user = factories.User()
        private_dataset = factories.Dataset(
            private=True,
            owner_org=factories.Organization()['id'],
            creator_user_id=user['id']
        )
        call_action(
            'package_patch',
            get_context(user['name']),
            id=private_dataset['id'],
            name="updated-name"
        )
        activity_stream = call_action(
            'package_activity_list',
            get_context(user['name']),
            id=private_dataset['id']
        )
        assert len(activity_stream) == 1
