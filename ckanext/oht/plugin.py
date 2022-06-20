import datetime
import logging
from collections import OrderedDict

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.uploader as uploader
import ckanext.blob_storage.helpers as blobstorage_helpers
import ckan.logic.auth as logic_auth
from ckan.lib.plugins import DefaultPermissionLabels
from giftless_client import LfsClient
from werkzeug.datastructures import FileStorage as FlaskFileStorage
from ckanext.oht.helpers import (
    get_dataset_from_id, get_facet_items_dict
)
import ckan.authz as authz

log = logging.getLogger(__name__)


class OHTPlugin(plugins.SingletonPlugin, DefaultPermissionLabels):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IPermissionLabels)
    plugins.implements(plugins.IAuthFunctions)

    # ITemplateHelpers
    def get_helpers(self):
        return {
            u'max_resource_size': uploader.get_max_resource_size,
            u'get_dataset_from_id': get_dataset_from_id,
            u'blob_storage_resource_filename': blobstorage_helpers.resource_filename,
            u'get_facet_items_dict': get_facet_items_dict
        }

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "oht")

    # IFacets
    def dataset_facets(self, facet_dict, package_type):
        new_fd = OrderedDict()
        new_fd['groups'] = plugins.toolkit._('Groups')
        new_fd['program_area'] = plugins.toolkit._('Program area')
        new_fd['tags'] = plugins.toolkit._('Tags')
        new_fd['year'] = plugins.toolkit._('Year')
        new_fd['res_format'] = plugins.toolkit._('Formats')
        return new_fd

    # IResourceController
    def before_create(self, context, resource):
        if _data_dict_is_resource(resource):
            _giftless_upload(context, resource)
            _update_resource_last_modified_date(resource)
        return resource

    def before_update(self, context, current, resource):
        if _data_dict_is_resource(resource):
            _giftless_upload(context, resource, current=current)
            _update_resource_last_modified_date(resource, current=current)
        return resource

    def get_dataset_labels(self, dataset_obj):
        """
        Stops private datasets from being visible to other members of the same
        organisation, whilst ensuring they remain visible to the creator user.

        This function is extending the default parent class behaviour found
        in ckan.lib.plugins.DefaultPermissionLabels.  We remove the label
        identifying the dataset as a member of the parent organisation, and
        replace it with the label identifying the creator user id.
        """
        labels = set(super(OHTPlugin, self).get_dataset_labels(dataset_obj))

        if dataset_obj.owner_org:
            labels.discard(f'member-{dataset_obj.owner_org}')
            labels.add(f'creator-{dataset_obj.creator_user_id}')

        return list(labels)

    def get_auth_functions(self):
        return {
            'package_update': _package_update_auth_function,
            'package_collaborator_create': _creators_can_manage_collaborators,
            'package_collaborator_delete': _creators_can_manage_collaborators,
            'package_collaborator_list': _creators_can_manage_collaborators
        }


@toolkit.chained_auth_function
def _creators_can_manage_collaborators(next_auth, context, data_dict):
    """
    Explicitly ensures that dataset creators can always edit collaborators.
    """
    user = context['user']
    model = context['model']

    package = model.Package.get(data_dict['id'])
    user_obj = model.User.get(user)

    if package.creator_user_id == user_obj.id:
        return {'success': True}

    else:
        return next_auth(context, data_dict)


@toolkit.auth_disallow_anonymous_access
def _package_update_auth_function(context, data_dict):
    """
    Explicitly ensures that only collaborators and creators can edit data.
    """
    user = context['auth_user_obj']
    package = logic_auth.get_package_object(context, data_dict)

    is_editor_collaborator = (
        authz.check_config_permission('allow_dataset_collaborators') and
        authz.user_is_collaborator_on_dataset(
            user.id, package.id, ['admin', 'editor']
        )
    )
    is_dataset_creator = (user.id == package.creator_user_id)

    if is_dataset_creator or is_editor_collaborator:
        return {'success': True}
    else:
        return {
            'success': False,
            'msg': toolkit._(
                f'User {user.name} not authorized to edit package {package.id}'
            )
        }


def _giftless_upload(context, resource, current=None):
    attached_file = resource.pop('upload', None)
    if attached_file:
        if type(attached_file) == FlaskFileStorage:
            dataset_id = resource.get('package_id')
            if not dataset_id:
                dataset_id = current['package_id']
            dataset = toolkit.get_action('package_show')(
                context, {'id': dataset_id})
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

            lfs_prefix = blobstorage_helpers.resource_storage_prefix(dataset_name, org_name=org_name)
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


def _data_dict_is_resource(data_dict):
    return not (
            u'creator_user_id' in data_dict
            or u'owner_org' in data_dict
            or u'resources' in data_dict
            or data_dict.get(u'type') == u'dataset')


def _get_upload_authz_token(context, dataset_name, org_name):
    scope = 'obj:{}/{}/*:write'.format(org_name, dataset_name)
    authorize = toolkit.get_action('authz_authorize')
    if not authorize:
        raise RuntimeError("Cannot find authz_authorize; Is ckanext-authz-service installed?")
    authz_result = authorize(context, {"scopes": [scope]})
    if not authz_result or not authz_result.get('token', False):
        raise RuntimeError("Failed to get authorization token for LFS server")
    if len(authz_result['granted_scopes']) == 0:
        error = "You are not authorized to upload this resource."
        log.error(error)
        raise toolkit.NotAuthorized(error)
    return authz_result['token']
