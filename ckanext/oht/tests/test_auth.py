import pytest
from ckan.tests import factories
from ckan.tests.helpers import call_action
from ckanext.oht.tests import get_context
from ckan.plugins import toolkit


@pytest.mark.ckan_config("ckan.plugins", "oht scheming_datasets")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestAuth():

    def setup(self):
        self.user_1 = factories.User()
        self.user_2 = factories.User()
        self.org = factories.Organization(
            users=[
                {'name': self.user_1['name'], 'capacity': 'editor'},
                {'name': self.user_2['name'], 'capacity': 'editor'}
            ]
        )
        self.dataset_1 = factories.Dataset(
            owner_org=self.org['id'],
            type='oht',
            private=True,
            creator_user_id=self.user_1['id']
        )
        self.dataset_2 = factories.Dataset(
            owner_org=self.org['id'],
            type='oht',
            private=True,
            creator_user_id=self.user_2['id']
        )

    def test_users_cant_see_other_users_datasets(self):
        with pytest.raises(toolkit.NotAuthorized):

            call_action(
                'package_show',
                get_context(self.user_1),
                id=self.dataset_2['id']
            )

        with pytest.raises(toolkit.NotAuthorized):
            call_action(
                'package_show',
                get_context(self.user_2),
                id=self.dataset_1['id']
            )

    def test_editors_cant_edit_other_users_datasets(self):
        # TODO:
        pass
