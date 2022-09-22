import ckan.plugins.toolkit as toolkit
import secrets
import logging
import re
import random

log = logging.getLogger(__name__)


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

    return next_action(context, data_dict)


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
    for public CKAN instances. Use the IEmailAsUsername plugin
    interface to do this.
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
