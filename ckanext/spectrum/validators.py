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
