import pytest

import ckan.tests.factories as factories
from ckan.plugins import toolkit
from ckan.tests.helpers import call_action


@pytest.fixture
def organization():
    return factories.Organization()


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestPackageCreate():

    def test_should_complain_with_exception_when_dataset_type_invalid(self, organization):
        exception_message = "{'message': \"Type 'baad-type' is invalid, valid types are: " \
                               "'auto-generate-name-from-title, dataset'\""
        with pytest.raises(toolkit.ValidationError, match=exception_message) as e:
            call_action('package_create', name="some-name", type="baad-type", owner_org=organization['name'],
                        title="Dataset with missing title")

    def test_create_dataset_without_type_creates_one_with_default_type_of_dataset(self, organization):
        dataset = call_action('package_create', name="some-name", owner_org=organization['name'],
                              title="Dataset without type")

        assert dataset["type"] == "dataset"

    def test_create_dataset_with_valid_type(self, organization):
        dataset = call_action('package_create', name="some-name",
                              type="auto-generate-name-from-title",
                              title="Dataset with valid type",
                              owner_org=organization['name'])

        assert dataset["type"] == "auto-generate-name-from-title"
