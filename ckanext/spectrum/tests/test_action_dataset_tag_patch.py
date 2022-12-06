import pytest

import ckan.tests.factories as factories
from ckan.plugins import toolkit
from ckan.tests.helpers import call_action


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestDatasetTagPatch():

    def test_should_change_datasets_with_matching_tags_only(self):
        d1 = create_dataset(["draft", "influenza"], "d1")
        d2 = create_dataset(["consultations", "covid19"], "d2")
        d3 = create_dataset(["influenza", "covid19"], "d3")

        result = call_action(
            'dataset_tag_replace',
            q='name:*',
            tags={'draft': 'consultations', 'consultations': 'final'}
        )

        assert result['datasets_modified'] == 2

        assert_dataset_contains_only_tags(d1["id"], ["influenza", "consultations"])
        assert_dataset_contains_only_tags(d2["id"], ["final", "covid19"])
        assert_dataset_contains_only_tags(d3["id"], ["covid19", "influenza"])

    def test_should_complain_when_no_tags_passed(self):
        with pytest.raises(toolkit.ValidationError) as ex:
            call_action(
                'dataset_tag_replace',
                q='name:*'
            )
        assert str(ex.value) == "None - {'message': \"Must specify 'tags' dict of tags for update in form " \
                                "{'old_tag_name1': 'new_tag_name1', 'old_tag_name2': 'new_tag_name2'}\"}"


def create_dataset(tags_list, dataset_name):
    tags = [{"name": value} for value in tags_list]
    org = factories.Organization()
    dataset = factories.Dataset(
        type='auto-generate-name-from-title',
        id="test-id" + dataset_name,
        owner_org=org['id'],
        tags=tags,
        name=dataset_name
    )

    return call_action('package_show', id=dataset['id'])


def assert_dataset_contains_only_tags(dataset_id, expected_tags):
    dataset = call_action(
        'package_show', id=dataset_id
    )

    assert set([tag["name"] for tag in dataset["tags"]]) == set(expected_tags)