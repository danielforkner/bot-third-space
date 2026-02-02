"""
Test data factories for Third-Space API tests.

These factories will be fully implemented once models exist.
Currently provides placeholder structure for test development.
"""

# Note: Factory implementations will be added as models are created.
# This file serves as a placeholder for the test infrastructure.

# Example factory structure (to be implemented):
#
# import factory
# from factory import Faker, LazyAttribute
# from uuid import uuid4
#
# from app.models.user import User
#
#
# class UserFactory(factory.Factory):
#     """Factory for creating User test instances."""
#
#     class Meta:
#         model = User
#
#     id = LazyAttribute(lambda _: uuid4())
#     username = Faker("user_name")
#     email = Faker("email")
#     display_name = Faker("name")
