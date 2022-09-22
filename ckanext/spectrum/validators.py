from ckanext.scheming.validation import scheming_validator
from ckan.logic.validators import package_name_validator
from ckan.plugins.toolkit import ValidationError, _
from string import ascii_lowercase
from random import choice
import copy
import slugify


@scheming_validator
def generate_name_from_title(field, schema):

    def validator(key, data, errors, context):

        # Preserve the name when editing an existing package
        if context.get('package'):
            data[key] = context['package'].name
            return

        # Use the exact name given by the user if it exists
        if data[key]:
            return

        if not data[('title',)]:
            raise ValidationError({'title': ['Missing value']})

        title_slug = slugify.slugify(data[('title',)])
        data[key] = title_slug

        # Multiple attempts so alpha_id can be as short as possible
        for counter in range(10):
            package_name_errors = copy.deepcopy(errors)
            package_name_validator(key, data, package_name_errors, context)
            dataset_name_valid = package_name_errors[key] == errors[key]

            if dataset_name_valid:
                break

            alpha_id = ''.join(choice(ascii_lowercase) for i in range(3))
            new_dataset_name = "{}-{}".format(title_slug, alpha_id)
            data[key] = new_dataset_name
        else:
            raise ValidationError({'name': [_('Could not autogenerate a unique name.')]})

    return validator


def user_id_validator(key, data, errors, context):
    """
    Validate a new user id.

    The form of this validator is taken from the ckan core validator:
        user_name_validator
    """
    model = context['model']
    new_user_id = data[key]

    if not isinstance(new_user_id, str):
        raise ValidationError({'id': [_('User IDs must be strings')]})

    user = model.User.get(new_user_id)
    user_obj_from_context = context.get('user_obj')

    if user is not None:

        # A user with new_user_id already exists in the database.
        if user_obj_from_context and user_obj_from_context.name == user.name:
            # If there's a user_obj in context with the same id as the user
            # found in the db, then we must be doing a user_update and not
            # updating the user name, so don't return an error.
            return
        else:
            # Otherwise return an error: there's already another user with that
            # name, so you can create a new user with that name or update an
            # existing user's name to that name.
            errors[key].append(_('That user ID is not available.'))

    elif user_obj_from_context:
        old_user = model.User.get(user_obj_from_context.id)

        if old_user is not None and old_user.state != model.State.PENDING:
            errors[key].append(_('The user ID cannot be modified.'))
        else:
            return
