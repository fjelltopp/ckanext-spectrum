import mock
import pytest

import ckan.tests.factories as factories
from ckan.plugins.toolkit import ValidationError
from ckan.tests.helpers import call_action


@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestAutoGenerateNameFromTitle(object):

    def _create_dataset(self, **kwargs):
        return call_action(
            "package_create",
            type="auto-generate-name-from-title",
            title="North Pole Projection",
            **kwargs
        )

    def test_name_is_slugified_title(self):
        dataset = self._create_dataset()
        assert dataset["name"] == "north-pole-projection"

    def test_duplicate_titles(self):
        datasets = [self._create_dataset() for i in range(10)]
        for dataset in datasets:
            assert dataset["name"].startswith("north-pole-projection")

    def test_preserves_given_name(self):
        dataset = self._create_dataset(name="test-name")
        assert dataset["name"] == "test-name"

    def test_error_raised_if_given_name_exists(self):
        dataset = self._create_dataset()
        with pytest.raises(ValidationError, match="URL is already in use"):
            self._create_dataset(name=dataset["name"])

    def test_preserves_existing_dataset_name(self):
        dataset1, dataset2 = [self._create_dataset() for i in range(2)]
        call_action("package_delete", id=dataset1["id"])
        updated_dataset2 = call_action("package_update", **dataset2)
        assert updated_dataset2["name"] == dataset2["name"]

    def test_handles_deleted_datasets(self):
        dataset1, dataset2 = [self._create_dataset() for i in range(2)]
        call_action("package_delete", id=dataset2["id"])
        dataset3 = self._create_dataset(name=dataset2["name"])
        assert dataset3["name"] == dataset2["name"]

    @mock.patch("ckanext.spectrum.validators.choice", return_value="a")
    def test_many_failed_generation_attempts(self, mock_choice):
        self._create_dataset()
        self._create_dataset()
        with pytest.raises(ValidationError, match="Could not autogenerate"):
            self._create_dataset()

    def test_missing_title(self):
        with pytest.raises(ValidationError, match="title.*Missing value"):
            call_action("package_create", type="auto-generate-name-from-title")


@pytest.mark.ckan_config("ckan.plugins", "spectrum")
@pytest.mark.usefixtures("clean_db", 'with_plugins')
class TestUserIDValidator(object):

    def test_user_id_uniqueness(self):
        factories.User(id='test-id')
        with pytest.raises(ValidationError, match="ID is not available"):
            factories.User(id='test-id')

    def test_user_can_be_updated(self):
        user = factories.User(id='test-id')
        user['email'] = "newemail@test.org"
        assert call_action('user_update', **user)

    def test_id_cannot_match_existing_username(self):
        factories.User(name='test-id')
        with pytest.raises(ValidationError, match="ID is not available"):
            factories.User(id='test-id')
