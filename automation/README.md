# Automation Scripts

All deployment and setup scripts in one place.

## Scripts

| Script | Purpose |
|--------|---------|
| `setup-runner.sh` | **One-time setup** - installs GitHub Actions runner on Salam's machine |
| `setup_instance.sh` | Initial server setup (Docker, dependencies) |
| `deploy.sh` | Manual deploy script |
| `test_api.sh` | Test API endpoints |
| `run_worker.py` | Run Celery worker manually |
| `push_and_deploy.bat` | Windows batch for push + deploy |

## Quick Start (Salam's Machine)

```bash
cd ~/inference_engine/automation
chmod +x setup-runner.sh
./setup-runner.sh
```

After this one command, every `git push` to main auto-deploys.
