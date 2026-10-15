# Contributing to PulseNet

Thanks for your interest in improving PulseNet! This project began as a
course project at HCMUTE, and contributions are welcome.

## Getting started

1. Fork the repository and clone your fork.
2. Follow the [setup instructions in the README](README.md#quick-start) to
   get the server and firmware running locally.
3. Create a branch for your change:

   ```bash
   git checkout -b feat/my-feature
   ```

## Making changes

- Keep the architecture as described in the README: ESP32 student devices
  (BLE peripheral) → Raspberry Pi gateway → FastAPI backend → teacher
  dashboard.
- **Never commit secrets.** API keys belong in `backend/.env`, which is
  git-ignored. Use `backend/.env.example` as the template.
- Keep firmware dependencies minimal — the student device targets an
  ESP32-WROOM-32 with limited flash/RAM.
- Match the existing code style of the file you are editing.

## Testing

Before opening a pull request, run the backend integration suite — it
simulates a full classroom session with multiple devices and needs no
hardware:

```bash
cd PulseNet-server/backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python test_integration_e2e.py
```

All checks must pass. For firmware changes, build with
`pio run -d PulseNet-device` and test on real hardware if you can.

## Pull requests

1. Push your branch to your fork.
2. Open a pull request against `main` describing **what** changed and
   **why**.
3. Make sure CI (backend tests + firmware build) is green.

## Reporting issues

Use the [issue tracker](../../issues) and include:

- What you expected vs. what happened
- Steps to reproduce (server log excerpt, firmware serial monitor output)
- Environment: OS, Python version, board revision

## License

By contributing, you agree that your contributions will be licensed under
the [MIT License](LICENSE).
