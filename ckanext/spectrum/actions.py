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

    dataset.pop('id', None)
    dataset.pop('name', None)
    data_dict.pop('id', None)
    context.pop('package', None)

    dataset = {**dataset, **data_dict}
    resources = dataset.pop('resources', [])

    new_dataset = toolkit.get_action('package_create')(context, dataset)
    toolkit.get_action('package_relationship_create')(context, {
        'subject': new_dataset['id'],
        'object': dataset_id,
        'type': 'child_of'
    })

    for resource in resources:
        _duplicate_resource(context, resource, new_dataset['id'])

    return toolkit.get_action('package_show')(context, {'id': new_dataset['id']})


def _duplicate_resource(context, resource, new_dataset_id):
    resource['upload'] = _get_resource_upload(resource)
    resource['package_id'] = new_dataset_id

    resource.pop('id', None)
    resource.pop('size', None)
    resource.pop('sha256', None)
    resource.pop('lfs_prefix', None)
    resource.pop('url', None)

    toolkit.get_action('resource_create')(context, resource)


def _get_resource_upload(resource):
    filename = resource.get('url', "").split('/')[-1]
    download_response = download(resource['package_id'], resource['id'], filename)

    while str(download_response.status_code)[0] == '3':  # Redirected
        redirect_url = download_response.headers.get('Location')
        download_response = requests.get(redirect_url, stream=True)

    return FileStorage(BytesIO(download_response.content), filename, 'upload')
