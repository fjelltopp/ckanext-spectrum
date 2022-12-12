import mock
import pytest

import ckan.tests.factories as factories
from ckan.plugins.toolkit import ValidationError
from ckan.tests.helpers import call_action


@pytest.fixture
def user_dict():
    return {
        "id": "some_id",
        "name": "some_name",
        "email": "some_email@example.com"
    }


@pytest.fixture
def sysadmin_context():
    return {
        "user": factories.Sysadmin()["name"],
        "ignore_auth": False,
    }


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
class TestUserIDValidationRules(object):

    def test_when_user_id_is_not_unique_it_changes_into_random_id(self, user_dict, sysadmin_context):
        user = call_action("user_create", context=sysadmin_context, **user_dict)
        assert user["id"] == "some_id"

        user_dict["name"] = "some-other-name"
        user2 = call_action("user_create", context=sysadmin_context, **user_dict)

        assert user2["id"] != "some_id"

    def test_when_user_id_is_same_as_other_username_it_changes_into_random_id(self, user_dict, sysadmin_context):
        user = call_action("user_create", context=sysadmin_context, **user_dict)
        assert user["name"] == "some_name"

        user_dict["id"] = "some_name"
        user_dict["name"] = "some-other-name"
        user2 = call_action("user_create", context=sysadmin_context, **user_dict)

        assert user2["id"] != "some_id"

    def test_when_user_name_is_same_as_other_id_an_error_is_thrown(self, user_dict, sysadmin_context):
        user = call_action("user_create", context=sysadmin_context, **user_dict)
        assert user["id"] == "some_id"

        user_dict["id"] = "some_other_id"
        user_dict["name"] = "some_id"
        with pytest.raises(ValidationError, match="That login name is not available"):
            call_action("user_create", **user_dict)
