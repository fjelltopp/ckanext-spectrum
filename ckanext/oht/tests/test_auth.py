import pytest
from ckan.tests import factories
from ckan.tests.helpers import call_auth, call_action
from ckanext.oht.tests import get_context
from ckan.plugins import toolkit


@pytest.mark.usefixtures("clean_db")
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
            user=self.user_1
        )
        self.dataset_2 = factories.Dataset(
            owner_org=self.org['id'],
            type='oht',
            private=True,
            user=self.user_2
        )

    def test_users_cant_see_other_users_datasets(self):

        with pytest.raises(toolkit.NotAuthorized):
            call_auth(
                'package_show',
                get_context(self.user_1),
                id=self.dataset_2['id']
            )

        with pytest.raises(toolkit.NotAuthorized):
            call_auth(
                'package_show',
                get_context(self.user_2),
                id=self.dataset_1['id']
            )

    def test_users_cant_edit_other_users_datasets(self):

        with pytest.raises(toolkit.NotAuthorized):
            call_auth(
                'package_update',
                get_context(self.user_1),
                id=self.dataset_2['id']
            )

        with pytest.raises(toolkit.NotAuthorized):
            call_auth(
                'package_update',
                get_context(self.user_1),
                id=self.dataset_2['id']
            )

    def test_users_can_edit_own_datasets(self):
        assert call_auth(
            'package_update',
            get_context(self.user_1),
            id=self.dataset_1['id']
        )
        assert call_auth(
            'package_update',
            get_context(self.user_2),
            id=self.dataset_2['id']
        )

    def test_users_can_see_own_datasets(self):
        assert call_auth(
            'package_show',
            get_context(self.user_1),
            id=self.dataset_1['id'],
        )
        assert call_auth(
            'package_show',
            get_context(self.user_2),
            id=self.dataset_2['id'],
        )

    def test_collaborators_can_see_datasets(self):
        call_action(
            'package_collaborator_create',
            id=self.dataset_1['id'],
            user_id=self.user_2['id'],
            capacity='member'
        )
        assert call_auth(
            'package_show',
            get_context(self.user_2),
            id=self.dataset_1['id'],
        )

    def test_collaborators_can_edit_datasets(self):
        call_action(
            'package_collaborator_create',
            id=self.dataset_2['id'],
            user_id=self.user_1['id'],
            capacity='editor'
        )
        assert call_auth(
            'package_update',
            get_context(self.user_1),
            id=self.dataset_2['id'],
        )
