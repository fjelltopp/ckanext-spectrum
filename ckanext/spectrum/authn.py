import ckan.model as model
from flask import current_app


def substitute_user(substitute_user_id):
    substitute_user_obj = model.User.get(substitute_user_id)

    if not substitute_user_obj:
        return {
            "success": False,
            "error": {
                "__type": "Bad Request",
                "message": "CKAN-Substitute-User header does not "
                           "identify a valid CKAN user"
            }
        }, 400

    # Temporary fix: This should change once CKAN github issue 7581 is resolved
    # https://github.com/ckan/ckan/issues/7581
    current_app.login_manager._update_request_context_with_user(substitute_user_obj)

