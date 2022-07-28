import ckan.authz as authz
import ckan.logic.auth as logic_auth
import ckan.plugins.toolkit as toolkit


@toolkit.chained_auth_function
def creators_manage_collaborators(next_auth, context, data_dict):
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
def package_update(context, data_dict):
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
