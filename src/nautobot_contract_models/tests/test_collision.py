"""Lock the related_name namespace on Contract.status / Invoice.status.

These tests pin the Django model-level configuration that prevents the
reverse-accessor collision with nautobot-app-device-lifecycle's
ContractLCM.status. If anyone removes the explicit `related_name=` from
either StatusField, these tests catch it before the operator's
`nautobot-server check` does.

No DLC import or installation is required — the tests verify only our
local-side invariant. Manual end-to-end verification (Nautobot booting
with both apps installed) is documented in the release notes.
"""

from nautobot.core.testing import TestCase

from nautobot_contract_models.models import Contract, Invoice


class StatusFieldRelatedNameTests(TestCase):
    """Pin the namespaced related_name on every StatusField in this app."""

    def test_contract_status_related_name_is_namespaced(self):
        field = Contract._meta.get_field("status")
        self.assertEqual(field.remote_field.related_name, "contract_models_contracts")

    def test_invoice_status_related_name_is_namespaced(self):
        field = Invoice._meta.get_field("status")
        self.assertEqual(field.remote_field.related_name, "contract_models_invoices")

    def test_contract_status_reverse_query_name_does_not_clash(self):
        # The reverse query name (used as the FK lookup keyword from Status)
        # also follows the namespaced related_name. Confirms Django registered
        # the override correctly — without it, the query name defaults back
        # to the model name and collides with DLC's ContractLCM.
        field = Contract._meta.get_field("status")
        self.assertEqual(
            field.remote_field.get_accessor_name(),
            "contract_models_contracts",
        )

    def test_invoice_status_reverse_query_name_does_not_clash(self):
        field = Invoice._meta.get_field("status")
        self.assertEqual(
            field.remote_field.get_accessor_name(),
            "contract_models_invoices",
        )
