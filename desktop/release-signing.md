# Windows code signing (SmartScreen)

Unsigned `PLG.exe` triggers **Windows SmartScreen** (“Windows protected your PC”). Authenticode signing fixes this after reputation builds.

## Requirements

- **EV Code Signing Certificate** (recommended for new publishers) — DigiCert, Sectigo, SSL.com
- Or standard OV cert (slower SmartScreen trust buildup)
- Windows SDK **signtool.exe** (Visual Studio Build Tools)

## Build with signing

Set env vars before `build_plg.bat`:

```bat
set PLG_SIGN_CERT=CN=Your Company Name
set PLG_SIGN_TIMESTAMP=http://timestamp.digicert.com
build_plg.bat release
```

Or thumbprint:

```bat
set PLG_SIGN_THUMBPRINT=ABCD1234...
build_plg.bat release
```

`build_plg.bat` signs `dist\PLG.exe` after PyInstaller if `PLG_SIGN_CERT` or `PLG_SIGN_THUMBPRINT` is set.

## Manual sign

```bat
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist\PLG.exe
```

## Check signature

```bat
signtool verify /pa dist\PLG.exe
```

## Notarization

Not required on Windows (macOS only). Focus on Authenticode + consistent publisher name.

## CI

Store cert in Azure Key Vault / GitHub secret as PFX + password. Never commit PFX to git.
