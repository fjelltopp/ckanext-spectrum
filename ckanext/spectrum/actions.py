import ckan.plugins.toolkit as toolkit
import secrets


@toolkit.chained_action
def user_create(next_action, context, data_dict):
    """
    Autogenerates a password (if password is not provided).
    """

    if not data_dict.get('password'):
        data_dict['password'] = secrets.token_urlsafe(32)

    return next_action(context, data_dict)


def dataset_duplicate(context, data_dict):
    dataset_id = toolkit.get_or_bust(data_dict, 'id')
    dataset = toolkit.get_action('package_show')(context, {'id': dataset_id})
    resources = dataset.pop('resources', [])

    del dataset['id']
    del dataset['name']
    del data_dict['id']
    del context['package']

    dataset = {**dataset, **data_dict}
    new_dataset = toolkit.get_action('package_create')(context, dataset)

    for resource in resources:
        resource['package_id'] = new_dataset['id']
        toolkit.get_action('resource_create')(context, resource)

    return toolkit.get_action('package_show')(context, {'id': new_dataset['id']})
