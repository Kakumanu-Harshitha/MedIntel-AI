# Authentication module package
import importlib.util
import sys
import os

# Load the auth.py module dynamically to avoid circular imports
auth_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'auth.py')
spec = importlib.util.spec_from_file_location("auth_module", auth_module_path)
auth_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_module)

# Export the router and auth functions
router = auth_module.router
get_current_user = auth_module.get_current_user
get_current_owner = auth_module.get_current_owner
pwd_context = auth_module.pwd_context

__all__ = ['router', 'get_current_user', 'get_current_owner', 'pwd_context']