Gopackshot PrintModule — Distribution Readme

Contents:
- dist/dmg/Gopackshot_PrintModule-<version>.dmg
- dist/pkg/Gopackshot_PrintModule-<version>.pkg
- scripts/install_from_folder.command
- docs/INSTALL.txt (GUI/CLI steps)

Cloud Link (Ably):
- Configure via environment variables or QSettings:
  - GPP_CLOUD_ENABLED=1
  - GPP_CLOUD_AUTOCONNECT=1
  - GPP_ABLY_AUTH_URL=https://your-auth-url (preferred) or GPP_ABLY_KEY=key:xxx
  - GPP_ABLY_CHANNEL=gopackshot:print-module:default
  - GPP_ABLY_CLIENT_ID=your-machine
- In the app: Tools → Cloud Connect / Disconnect / Send Test

Printing:
- Ensure Brother QL printer is installed in CUPS.
- Default printer can be set via env QL_PRINTER or per-request payload.

Support:
- Templates are bundled under the app. You can choose an external Templates folder in the app.
- Runtime/temp assets are stored in ~/Library/Application Support/GopackshotPrintModule.

