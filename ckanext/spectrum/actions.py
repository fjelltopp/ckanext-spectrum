import ckan.plugins.toolkit as toolkit
import secrets
import logging
import re
import random

log = logging.getLogger(__name__)

allowed_package_search_params = {"q", "fq", "fq_list", "include_drafts", "include_private",
                                 "use_default_schema"}


def dataset_duplicate(context, data_dict):
    dataset_id_or_name = toolkit.get_or_bust(data_dict, 'id')
    dataset = toolkit.get_action('package_show')(context, {'id': dataset_id_or_name})
    dataset_id = dataset['id']

    dataset.pop('id', None)
    dataset.pop('name', None)
    data_dict.pop('id', None)
    context.pop('package', None)

    dataset = {**dataset, **data_dict}

    for resource in dataset.get('resources', []):
        del resource['id']
        del resource['package_id']

    duplicate_dataset = toolkit.get_action('package_create')(context, dataset)
    _record_dataset_duplication(dataset_id, duplicate_dataset['id'], context)

    return toolkit.get_action('package_show')(context, {'id': duplicate_dataset['id']})


@toolkit.chained_action
def user_create(next_action, context, data_dict):
    """
    Autogenerates a password and username (if password or username is not provided).
    """

    if not data_dict.get('password'):
        data_dict['password'] = secrets.token_urlsafe(32)

    if data_dict.get('name'):
        return next_action(context, data_dict)

    if not data_dict.get('email'):
        raise toolkit.ValidationError(toolkit._("Must specify either a name or an email"))

    email = data_dict['email']
    username = _get_random_username_from_email(email, context['model'])
    data_dict['name'] = username

    created_user = next_action(context, data_dict)

    default_org_name = toolkit.config.get('ckanext.spectrum.default_organization', 'spectrum')
    org_member_dict = {'id': default_org_name, 'username': created_user['name'], 'role': 'editor'}
    try:
        ignore_auth_context = {"user": context["user"], "ignore_auth": True}
        toolkit.get_action('organization_member_create')(ignore_auth_context, org_member_dict)
    except toolkit.ValidationError:
        log.error(f"Failed to add newly created user: {created_user['name']} to org: {default_org_name}. "
                  f"User account got created successfully.")
    return created_user


def dataset_tag_replace(context, data_dict):
    if 'tags' not in data_dict or not isinstance(data_dict['tags'], dict):
        raise toolkit.ValidationError(toolkit._(
            "Must specify 'tags' dict of tags for update in form "
            "{'old_tag_name1': 'new_tag_name1', 'old_tag_name2': 'new_tag_name2'}"))

    tags = data_dict.pop("tags")
    package_search_params = _restrict_datasets_to_those_with_tags(data_dict, tags)

    datasets = toolkit.get_action('package_search')(context, package_search_params).get('results', [])

    _check_user_access_to_all_datasets(context, datasets)
    _update_tags(context, datasets, tags)

    return {'datasets_modified': len(datasets)}


def _check_user_access_to_all_datasets(context, datasets):
    for ds in datasets:
        toolkit.check_access('package_patch', context, {"id": ds['id']})


def _restrict_datasets_to_those_with_tags(package_search_params, tags):
    fq_tag_restriction = _create_fq_tag_restriction(tags)

    if 'fq' in package_search_params:
        original_fq = package_search_params['fq']
        package_search_params['fq'] = f"({original_fq}) AND ({fq_tag_restriction})"
    else:
        package_search_params['fq'] = f"({fq_tag_restriction})"

    return package_search_params


def _update_tags(context, datasets, tags_to_be_replaced):
    dataset_patch_action = toolkit.get_action('package_patch')

    for ds in datasets:
        final_tags = _prepare_final_tag_list(ds['tags'], tags_to_be_replaced)
        dataset_patch_action(context, {'id': ds['id'], 'tags': final_tags})


def _prepare_final_tag_list(original_tags, tags_to_be_replaced):
    final_tags = []
    for tag in original_tags:
        tag_name = tag['name']
        final_tags.append({"name": tags_to_be_replaced[tag_name] if tag_name in tags_to_be_replaced else tag_name})

    return final_tags


def _create_fq_tag_restriction(tags):
    return " OR ".join([f"tags:{key}" for key in tags])


def _record_dataset_duplication(dataset_id, new_dataset_id, context):
    # We should probably use activities to record duplication in CKAN 2.10

    relationship = {
        'subject': new_dataset_id,
        'object': dataset_id,
        'type': 'child_of'
    }

    try:
        current_activity_id = toolkit.get_action('package_activity_list')(
            context,
            {'id': dataset_id}
        )[0]['id']
        relationship['comment'] = f"Duplicated from activity {current_activity_id}"
    except Exception as e:
        log.error(f"Failed to get current activity for package {dataset_id} ...")
        log.exception(e)

    try:
        toolkit.get_action('package_relationship_create')(context, relationship)
    except Exception as e:
        log.error(f"Failed to record duplication of {dataset_id} to {new_dataset_id} ...")
        log.exception(e)


def _get_random_username_from_email(email, model):
    """
    This function is copied from a CKAN core private function:
        ckan.logic.action.create._get_random_username_from_email
    Github permalink:
        https://github.com/ckan/ckan/blob/0a596b8394dbf9582902853ad91450d2c0d7959b/ckan/logic/action/create.py#L1102-L1116

    The function has been deployed and used across a plethora of CKAN
    instances, which is why we are adopting it here.

    WARNING: This logic reveals part of the user's email address
    as their username.  Fjelltopp recommends overriding this logic
    for public CKAN instances.
    """

    localpart = email.split('@')[0]
    cleaned_localpart = re.sub(r'[^\w]', '-', localpart).lower()

    # if we can't create a unique user name within this many attempts
    # then something else is probably wrong and we should give up
    max_name_creation_attempts = 100

    for i in range(max_name_creation_attempts):
        random_number = random.SystemRandom().random() * 10000
        name = '%s-%d' % (cleaned_localpart, random_number)
        if not model.User.get(name):
            return name

    return cleaned_localpart
