import ckan.plugins.toolkit as toolkit
from ckanext.blob_storage.blueprints import download
from werkzeug.datastructures import FileStorage
from io import BytesIO
import secrets
import requests


@toolkit.chained_action
def user_create(next_action, context, data_dict):
    """
    Autogenerates a password (if password is not provided).
    """

    if not data_dict.get('password'):
        data_dict['password'] = secrets.token_urlsafe(32)

    return next_action(context, data_dict)


def dataset_duplicate(context, data_dict):
    dataset_id_or_name = toolkit.get_or_bust(data_dict, 'id')
    dataset = toolkit.get_action('package_show')(context, {'id': dataset_id_or_name})
    dataset_id = dataset['id']
    resources = dataset.pop('resources', [])

    del dataset['id']
    del dataset['name']
    del data_dict['id']
    del context['package']

    dataset = {**dataset, **data_dict}
    new_dataset = toolkit.get_action('package_create')(context, dataset)

    for resource in resources:
        resource['upload'] = _get_resource_file_storage(dataset_id, resource)
        resource['package_id'] = new_dataset['id']

        del resource['id']
        del resource['size']
        del resource['sha256']
        del resource['lfs_prefix']
        del resource['url']

        toolkit.get_action('resource_create')(context, resource)

    return toolkit.get_action('package_show')(context, {'id': new_dataset['id']})


def _get_resource_file_storage(dataset_id, resource):
    filename = resource.get('url', "").split('/')[-1]
    blob_storage_response = download(dataset_id, resource['id'], filename)
    file_location = blob_storage_response.headers.get('Location')
    file_response = requests.get(file_location, stream=True)
    return FileStorage(BytesIO(file_response.content), filename, 'upload')
