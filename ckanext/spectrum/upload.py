import datetime
import logging
from giftless_client import LfsClient
from werkzeug.datastructures import FileStorage as FlaskFileStorage
import ckanext.blob_storage.helpers as blobstorage_helpers
from ckanext.activity.model import Activity
import ckan.plugins.toolkit as toolkit


log = logging.getLogger(__name__)


def add_activity(context, data_dict, activity_type):
    user = context['model'].User.by_name(context['user'])
    user_id = getattr(user, 'id', "UnknownUser")
    package = context.get("package", context['model'].Package.get(data_dict["name"]))
    activity = Activity.activity_stream_item(package, activity_type, user_id)
    context['session'].add(activity)
    context["session"].commit()


def handle_giftless_uploads(context, resource, current=None):
    _giftless_upload(context, resource, current=current)
    _update_resource_last_modified_date(resource, current=current)


def _giftless_upload(context, resource, current=None):
    attached_file = resource.pop('upload', None)

    if attached_file:

        if type(attached_file) == FlaskFileStorage:
            dataset_id = resource.get('package_id')

            if not dataset_id:
                dataset_id = current['package_id']

            dataset = toolkit.get_action('package_show')(
                context, {'id': dataset_id}
            )
            dataset_name = dataset['name']
            org_name = dataset.get('organization', {}).get('name')
            authz_token = _get_upload_authz_token(
                context,
                dataset_name,
                org_name
            )
            lfs_client = LfsClient(
                lfs_server_url=blobstorage_helpers.server_url(),
                auth_token=authz_token,
                transfer_adapters=['basic']
            )
            uploaded_file = lfs_client.upload(
                file_obj=attached_file,
                organization=org_name,
                repo=dataset_name
            )
            lfs_prefix = blobstorage_helpers.resource_storage_prefix(
                dataset_name,
                org_name=org_name
            )

            resource.update({
                'url_type': 'upload',
                'last_modified': datetime.datetime.utcnow(),
                'sha256': uploaded_file['oid'],
                'size': uploaded_file['size'],
                'url': attached_file.filename,
                'lfs_prefix': lfs_prefix
            })


def _update_resource_last_modified_date(resource, current=None):

    if current is None:
        current = {}

    for key in ['url_type', 'lfs_prefix', 'sha256', 'size', 'url']:
        current_value = str(current.get(key) or '')
        resource_value = str(resource.get(key) or '')

        if current_value != resource_value:
            resource['last_modified'] = datetime.datetime.utcnow()
            return


def _get_upload_authz_token(context, dataset_name, org_name):
    scope = 'obj:{}/{}/*:write'.format(org_name, dataset_name)
    authorize = toolkit.get_action('authz_authorize')

    if not authorize:
        raise RuntimeError(
            "Cannot find authz_authorize; Is ckanext-authz-service installed?"
        )

    authz_result = authorize(context, {"scopes": [scope]})

    if not authz_result or not authz_result.get('token', False):
        raise RuntimeError("Failed to get authorization token for LFS server")

    if len(authz_result['granted_scopes']) == 0:
        error = "You are not authorized to upload this resource."
        log.error(error)
        raise toolkit.NotAuthorized(error)

    return authz_result['token']

