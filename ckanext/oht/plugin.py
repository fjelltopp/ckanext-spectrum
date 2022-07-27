import logging
from collections import OrderedDict
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.uploader as uploader
import ckanext.blob_storage.helpers as blobstorage_helpers
from ckan.lib.plugins import DefaultPermissionLabels

from ckanext.oht.helpers import (
    get_dataset_from_id, get_facet_items_dict
)
import ckanext.oht.authz as oht_authz
import ckanext.oht.authn as oht_authn
import ckanext.oht.upload as oht_upload
import ckanext.oht.actions as oht_actions
import ckanext.oht.validators as oht_validators

log = logging.getLogger(__name__)


class OHTPlugin(plugins.SingletonPlugin, DefaultPermissionLabels):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IPermissionLabels)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IValidators)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IAuthenticator, inherit=True)

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
        new_fd['type'] = plugins.toolkit._('Projection Types')
        new_fd['country_name'] = plugins.toolkit._('Countries')
        new_fd['tags'] = plugins.toolkit._('Tags')
        return new_fd

    # IResourceController
    def before_create(self, context, resource):
        oht_upload.handle_giftless_uploads(context, resource)
        return resource

    def before_update(self, context, current, resource):
        oht_upload.handle_giftless_uploads(context, resource, current=current)
        return resource

    # IPermissionLabels
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

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'package_update': oht_authz.package_update,
            'package_collaborator_create': oht_authz.creators_can_manage_collaborators,
            'package_collaborator_delete': oht_authz.creators_can_manage_collaborators,
            'package_collaborator_list': oht_authz.creators_can_manage_collaborators
        }

    # IActions
    def get_actions(self):
        return {
            'user_create': oht_actions.user_create
        }

    # IValidators
    def get_validators(self):
        return {
            'auto_generate_name_from_title': oht_validators.auto_generate_name_from_title
        }

    # IPackageContoller
    def after_update(self, context, data_dict):
        if data_dict.get('private'):
            oht_upload.add_activity(context, data_dict, "changed")

    def after_create(self, context, data_dict):
        if data_dict.get('private'):
            oht_upload.add_activity(context, data_dict, "new")

    # IAuthenticator
    def identify(self):
        """
        Allows sysadmins to send requests "on behalf" of a substitute user. This is
        done by setting a HTTP Header in the requests "CKAN-Substitute-User" to be the
        username or user id of another CKAN user.
        """

        if not oht_authn.is_sysadmin():
            return {
                "success": False,
                "error": {
                    "__type": "Not Authorized",
                    "message": "Must be a system administrator to perform this action."
                }
            }, 403

        substitute_user_id = toolkit.request.headers.get('CKAN-Substitute-User')

        if substitute_user_id:
            return oht_authn.substitute_user(substitute_user_id)
