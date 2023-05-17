import logging
from collections import OrderedDict

import ckanext.blob_storage.helpers as blobstorage_helpers

import ckan.lib.uploader as uploader
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.spectrum.actions as spectrum_actions
import ckanext.spectrum.authn as spectrum_authn
import ckanext.spectrum.authz as spectrum_authz
import ckanext.spectrum.upload as spectrum_upload
import ckanext.spectrum.validators as spectrum_validators
from ckan.lib.plugins import DefaultPermissionLabels
from ckanext.spectrum.helpers import (
    get_dataset_from_id, get_facet_items_dict
)
from ckan.common import config_declaration

log = logging.getLogger(__name__)


class SpectrumPlugin(plugins.SingletonPlugin, DefaultPermissionLabels):

    plugins.implements(plugins.IConfigurable)
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
        toolkit.add_resource("assets", "spectrum")

    # IConfigurable
    def configure(self, config):
        """
        Temporary fix to CKAN Github issue 7593.
        https://github.com/ckan/ckan/issues/7593
        This should be removed when the issue is resolved.
        """
        config_declaration.normalize(config)

    # IFacets
    def dataset_facets(self, facet_dict, package_type):
        new_fd = OrderedDict()
        new_fd['type'] = plugins.toolkit._('Projection Types')
        new_fd['country_name'] = plugins.toolkit._('Countries')
        new_fd['tags'] = plugins.toolkit._('Tags')
        return new_fd

    # IResourceController
    def before_create(self, context, resource):
        spectrum_upload.handle_giftless_uploads(context, resource)
        return resource

    def before_update(self, context, current, resource):
        spectrum_upload.handle_giftless_uploads(context, resource, current=current)
        return resource

    # IPermissionLabels
    def get_dataset_labels(self, dataset_obj):
        """
        Stops private datasets from being visible to other members of the same
        organisation, whilst ensuring they remain visible to the creator user.

        This function is extending the default parent class behaviour found
        in ckan.lib.plugins.DefaultPermissionLabels. We remove the label
        identifying the dataset as a member of the parent organisation, and
        replace it with the label identifying the creator user id.
        """
        labels = set(super(SpectrumPlugin, self).get_dataset_labels(dataset_obj))

        if dataset_obj.owner_org:
            labels.discard(f'member-{dataset_obj.owner_org}')
            labels.add(f'creator-{dataset_obj.creator_user_id}')

        return list(labels)

    # IAuthFunctions
    def get_auth_functions(self):
        return {
            'package_update': spectrum_authz.package_update,
            'package_collaborator_create': spectrum_authz.creators_manage_collaborators,
            'package_collaborator_delete': spectrum_authz.creators_manage_collaborators,
            'package_collaborator_list': spectrum_authz.creators_manage_collaborators
        }

    # IActions
    def get_actions(self):
        return {
            'user_create': spectrum_actions.user_create,
            'dataset_duplicate': spectrum_actions.dataset_duplicate,
            'package_create': spectrum_actions.package_create,
            'dataset_tag_replace': spectrum_actions.dataset_tag_replace
        }

    # IValidators
    def get_validators(self):
        return {
            'auto_generate_name_from_title': spectrum_validators.generate_name_from_title
        }

    # IPackageContoller
    def after_dataset_delete(self, context, data_dict):
        package_data = toolkit.get_action('package_show')(context, data_dict)
        if package_data.get('private'):
            spectrum_upload.add_activity(context, package_data, "changed")

    def after_dataset_update(self, context, data_dict):
        if data_dict.get('private'):
            spectrum_upload.add_activity(context, data_dict, "changed")

    def after_dataset_create(self, context, data_dict):
        if data_dict.get('private'):
            spectrum_upload.add_activity(context, data_dict, "new")

    # IAuthenticator
    def identify(self):
        """
        Requires all API requests to be made by a registered sysadmin user.

        Allows API requests to be sent "on behalf" of a substitute user. This is
        done by setting a HTTP Header in the requests "CKAN-Substitute-User" to be the
        username or user id of another CKAN user.
        """

        if toolkit.request.path.startswith('/api/') or ('/download/' in toolkit.request.path):
            user_is_sysadmin = getattr(toolkit.current_user, 'sysadmin', False)
            if not user_is_sysadmin:
                return {
                    "success": False,
                    "error": {
                        "__type": "Not Authorized",
                        "message": "Must be a system administrator."
                    }
                }, 403

            substitute_user_id = toolkit.request.headers.get('CKAN-Substitute-User')

            if substitute_user_id:
                return spectrum_authn.substitute_user(substitute_user_id)
