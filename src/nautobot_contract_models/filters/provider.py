"""FilterSet for :class:`ServiceProvider`."""

from nautobot.apps.filters import NautobotFilterSet, SearchFilter

from nautobot_contract_models.models import ServiceProvider


class ServiceProviderFilterSet(NautobotFilterSet):
    """List-view filter set for :class:`ServiceProvider`."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "account_number": "icontains",
            "description": "icontains",
            "comments": "icontains",
        },
    )

    class Meta:
        """Meta."""

        model = ServiceProvider
        fields = ["id", "name", "account_number", "support_phone"]
