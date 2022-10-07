import pytest
from ckan.tests.helpers import call_action
from ckanext.spectrum.actions import user_create, _record_dataset_duplication
import ckan.tests.factories as factories
from ckanext.spectrum.tests import get_context
from ckan.plugins import toolkit

@pytest.fixture
def dataset():
    org = factories.Organization()
    dataset = factories.Dataset(
        type='auto-generate-name-from-title',
        id="test-id",
        owner_org=org['id']
    )
    resources = []
    for i in range(3):
        resources.append(factories.Resource(package_id=dataset['id']))
    return call_action('package_show', id=dataset['id'])


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestDatasetDuplicate():

    def test_dataset_metadata_duplicated(self, dataset):
        result = call_action(
            'dataset_duplicate',
            id=dataset['id'],
            name="duplicated-dataset"
        )
        fields = ['title', 'notes', 'private', 'num_resources']
        duplicated = [result[field] == dataset[field] for field in fields]
        assert all(duplicated), f"Duplication failed: {zip(fields, duplicated)}"

    def test_dataset_metadata_not_duplicated(self, dataset):
        result = call_action(
            'dataset_duplicate',
            id=dataset['id'],
            name="duplicated-dataset"
        )
        fields = ['name', 'id']
        not_duplicated = [result[field] != dataset[field] for field in fields]
        assert all(not_duplicated), f"Duplication occured: {zip(fields, not_duplicated)}"

    def test_resource_metadata_duplicated(self, dataset):
        result = call_action(
            'dataset_duplicate',
            id=dataset['id'],
            name="duplicated-dataset"
        )
        assert len(dataset['resources']) == len(result['resources'])
        fields = ['name']

        for i in range(len(dataset['resources'])):
            for f in fields:
                duplicated = dataset['resources'][i][f] == result['resources'][i][f]
                assert duplicated, f"Field {f} did not duplicate for resource {i}"

    def test_dataset_not_found(self):
        with pytest.raises(toolkit.ObjectNotFound):
            call_action(
                'dataset_duplicate',
                id='non-existant-id',
                name="duplicated-dataset"
            )

    @pytest.mark.parametrize('key, value', [
        ('notes', 'Some new notes'),
        ('title', 'A new title'),
        ('private', True),
        ('resources', [])
    ])
    def test_metadata_overidden(self, key, value, dataset):
        data_dict = {
            'id': dataset['id'],
            'name': "duplicated-dataset",
            key: value
        }
        result = call_action('dataset_duplicate', **data_dict)
        assert result[key] == value

    def test_record_duplication(self):
        user = factories.User()
        dataset1 = factories.Dataset(user=user)
        dataset2 = factories.Dataset(user=user)
        call_action(
            'package_patch',
            id=dataset1['id'],
            title='New Title To Create Activity ID'
        )
        _record_dataset_duplication(
            dataset1['id'],
            dataset2['id'],
            get_context(user['name'])
        )
        relationships_list = call_action(
            'package_relationships_list',
            id=dataset1['id'],
            id2=dataset2['id']
        )
        assert relationships_list[0]['subject'] == dataset1['name']
        assert relationships_list[0]['type'] == 'parent_of'
        assert relationships_list[0]['object'] == dataset2['name']
        assert relationships_list[0]['comment'].startswith('Duplicated from activity ')
