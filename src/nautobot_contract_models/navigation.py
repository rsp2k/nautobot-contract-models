"""Navigation menu wiring for the contract-models plugin.

Adds a top-level "Contracts" tab to Nautobot's left sidebar with one group
("Contracts") containing four list-view links — one per model. The
:class:`NavMenuAddButton` on each item gives the canonical "+" button that
links straight to the create form.

The viewset router (urls.py) is what produces the URL names referenced here
(``plugins:nautobot_contract_models:<model>_list`` and ``_add``).
"""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Contracts",
        weight=1500,
        groups=(
            NavMenuGroup(
                name="Contracts",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_contract_models:contract_list",
                        name="Contracts",
                        permissions=["nautobot_contract_models.view_contract"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_contract_models:contract_add",
                                permissions=["nautobot_contract_models.add_contract"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_contract_models:invoice_list",
                        name="Invoices",
                        permissions=["nautobot_contract_models.view_invoice"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_contract_models:invoice_add",
                                permissions=["nautobot_contract_models.add_invoice"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_contract_models:serviceprovider_list",
                        name="Service Providers",
                        permissions=["nautobot_contract_models.view_serviceprovider"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_contract_models:serviceprovider_add",
                                permissions=["nautobot_contract_models.add_serviceprovider"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_contract_models:contractassignment_list",
                        name="Assignments",
                        permissions=["nautobot_contract_models.view_contractassignment"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_contract_models:contractassignment_add",
                                permissions=["nautobot_contract_models.add_contractassignment"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Reports",
                weight=200,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_contract_models:contract_renewal_calendar",
                        name="Renewal Calendar",
                        permissions=["nautobot_contract_models.view_contract"],
                    ),
                ),
            ),
        ),
    ),
)
