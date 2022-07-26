import pytest
import mock
from ckan.tests.helpers import call_action
from ckan.plugins.toolkit import ValidationError


def create_dataset(**kwargs):
    return call_action(
        "package_create",
        type="auto-generate-name-from-title",
        title="North Pole Projection",
        **kwargs
    )


@pytest.mark.ckan_config("ckan.plugins", "oht scheming_datasets")
@pytest.mark.usefixtures("clean_db", "clean_index", "with_plugins")
class TestAutoGenerateNameFromTitle(object):

    def test_name_is_slugified_title(self):
        dataset = create_dataset()
        assert dataset["name"] == "north-pole-projection"

    def test_duplicate_titles(self):
        datasets = [create_dataset() for i in range(10)]
        for dataset in datasets:
            assert dataset["name"].startswith("north-pole-projection")

    def test_preserves_given_name(self):
        dataset = create_dataset(name="test-name")
        assert dataset["name"] == "test-name"

    def test_error_raised_if_given_name_exists(self):
        dataset = create_dataset()
        with pytest.raises(ValidationError, match="URL is already in use"):
            create_dataset(name=dataset["name"])

    def test_preserves_existing_dataset_name(self):
        dataset1, dataset2 = [create_dataset() for i in range(2)]
        call_action("package_delete", id=dataset1["id"])
        updated_dataset2 = call_action("package_update", **dataset2)
        assert updated_dataset2["name"] == dataset2["name"]

    def test_handles_deleted_datasets(self):
        dataset1, dataset2 = [create_dataset() for i in range(2)]
        call_action("package_delete", id=dataset2["id"])
        dataset3 = create_dataset(name=dataset2["name"])
        assert dataset3["name"] == dataset2["name"]

    @mock.patch("ckanext.oht.validators.choice", return_value="a")
    def test_many_failed_generation_attempts(self, mock_choice):
        create_dataset()
        create_dataset()
        with pytest.raises(ValidationError, match="Could not autogenerate"):
            create_dataset()

