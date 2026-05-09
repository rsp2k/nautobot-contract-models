# Uninstalling the App

To completely remove `nautobot-contract-models` from a Nautobot install:

## 1. Drop the schema

```shell
nautobot-server migrate nautobot_contract_models zero
```

This rolls back every migration in the plugin, dropping all its tables — `Contract`, `Invoice`, `ServiceProvider`, `ContractAssignment`, `ContractAttachment`, `InvoiceAttachment`, `CostSnapshot`. **All contract data is destroyed by this step.** Take a database dump first if you may want it back.

## 2. Disable the app

Edit `nautobot_config.py`:

- Remove `"nautobot_contract_models"` from `PLUGINS`
- Remove the `"nautobot_contract_models"` block from `PLUGINS_CONFIG`

## 3. Uninstall the package

```shell
pip uninstall nautobot-contract-models
```

If you added it to `local_requirements.txt`, remove that line too.

## 4. Restart services

```shell
sudo systemctl restart nautobot nautobot-worker
```

## 5. Clean up media files (optional)

The plugin stores file attachments under:

- `MEDIA_ROOT/contract_attachments/`
- `MEDIA_ROOT/invoice_attachments/`

These directories are NOT removed automatically. Delete them if you want the disk space back:

```shell
rm -rf $MEDIA_ROOT/contract_attachments/ $MEDIA_ROOT/invoice_attachments/
```

(`MEDIA_ROOT` is the path configured in `nautobot_config.py`; on the dev container it's `/opt/nautobot/media/`.)

## 6. Clean up scheduled jobs (optional)

Any `Scheduled Jobs` you configured against this plugin's Jobs (Renewal Check, Coverage Gap, Cost Report, Cost History, Cost Anomaly) will fail silently after the package is removed. Delete them under **Jobs → Scheduled Jobs**.
