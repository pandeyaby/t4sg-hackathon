# Farmers for Forests (Flutter)

Cross‑platform Flutter app for macOS, iOS, Android, and Web.

## Prerequisites

- Flutter SDK installed (`flutter --version`)
- For iOS/macOS: Xcode installed + `xcode-select` configured
- For Android: Android SDK + emulator/device (optional)

## Configure Backend

Start the backend (from repo root):

```bash
cd backend/src
QUALITY_ASSESSMENT_MODE=stub USE_GOOGLE_VISION=false USE_TESSERACT=false USE_TESSERACT_CLI=true USE_RAPIDFUZZ=false ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8004
```

In the app UI, set **API Base URL**:
- macOS / iOS Simulator / Web: `http://127.0.0.1:8004`
- Android Emulator: `http://10.0.2.2:8004`
- Physical iPhone: `http://<your-mac-ip>:8004`

## Run on macOS

```bash
flutter run -d macos
```

## Run on iOS (Simulator)

```bash
flutter run -d "iPhone 17 Pro Max"
```

## Run on Android (Emulator)

```bash
flutter run -d emulator-5554
```

## Run on Web (Chrome)

```bash
flutter run -d chrome
```

## Build APK (Android)

```bash
flutter build apk
```

## Notes

- macOS sandbox requires network + file picker entitlements (already configured).
- “Sync When Online” uses local SQLite and re‑submits pending documents.
