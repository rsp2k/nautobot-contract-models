"""Integration tests for the contract-models plugin.

These run inside the dev container via ``make test`` (which calls
``nautobot-server test nautobot_contract_models``) — the Django test
runner discovers them in this package.

The host-pytest tests at ``<repo>/tests/`` are a *different* test tree:
they only exercise top-level package import, with the conftest there
mocking out the entire Nautobot stack. Don't put real-Django tests in
that tree — the metaclass mocks make hierarchy-touching tests fail with
``TypeError: metaclass conflict``.
"""
