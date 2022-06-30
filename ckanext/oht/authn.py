import ckan.model as model
from ckan.views import _identify_user_default
import ckan.plugins.toolkit as toolkit


def substitute_user(substitute_user_id):
    # Not ideal, but this private import is the only way to use core CKAN logic.
    _identify_user_default()
    sysadmin = toolkit.g.userobj and toolkit.g.userobj.sysadmin

    if not sysadmin:
        return {
            "success": False,
            "error": {
                "__type": "Not Authorized",
                "message": "User not authorized to send requests "
                           "with CKAN-Substitute-User header"
            }
        }, 403

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

    toolkit.g.user = substitute_user_id
    toolkit.g.userobj = substitute_user_obj
