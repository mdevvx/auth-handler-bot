"""
UI package initialization
Contains all UI components: embeds, views, and modals
"""

from .embeds import (
    create_auth_embed,
    create_logout_embed,
    create_success_embed,
    create_error_embed,
    create_info_embed,
    create_warning_embed,
    create_signup_success_embed,
    create_login_success_embed,
)

from .views import AuthView, LogoutView, LogoutConfirmationView

from .modals import LoginModal

__all__ = [
    # Embeds
    "create_auth_embed",
    "create_logout_embed",
    "create_success_embed",
    "create_error_embed",
    "create_info_embed",
    "create_warning_embed",
    "create_signup_success_embed",
    "create_login_success_embed",
    # Views
    "AuthView",
    "LogoutView",
    "LogoutConfirmationView",
    # Modals
    "LoginModal",
]
