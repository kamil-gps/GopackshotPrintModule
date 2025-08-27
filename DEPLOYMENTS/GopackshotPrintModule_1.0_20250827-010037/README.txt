Gopackshot PrintModule - Deployment Kit

Contents:
- Gopackshot PrintModule.app
- Templates/ (starter templates)
- Install.command (copies app to Applications, seeds Templates, tries to start CUPS)

Install:
1) Double-click Install.command
2) If asked, enter your password to start CUPS
3) The app will launch when done

Templates default location:
- ~/Library/Application Support/GopackshotPrintModule/Templates

Cloud (optional):
- To enable Ably without UI steps, run:
  defaults write com.Gopackshot.ImageFlowPrint ably.api_key -string "YOUR_ABLY_KEY"
  defaults write com.Gopackshot.ImageFlowPrint ably.auth_url -string "https://your-auth"
  defaults write com.Gopackshot.ImageFlowPrint ably.channel -string "gopackshot:print-module:default"
  defaults write com.Gopackshot.ImageFlowPrint cloudEnabled -bool TRUE
  defaults write com.Gopackshot.ImageFlowPrint cloudAutoconnect -bool TRUE

Printing:
- Ensure your Brother QL printer is installed in System Settings > Printers
- Default printer used if not set: Brother_QL_1100

Uninstall:
- Delete /Applications/Gopackshot PrintModule.app (or ~/Applications/...)
- Optionally remove prefs: rm ~/Library/Preferences/com.Gopackshot.ImageFlowPrint.plist
- Optionally remove data: rm -rf "~/Library/Application Support/GopackshotPrintModule"

