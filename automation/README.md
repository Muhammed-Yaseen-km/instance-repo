# Automation Scripts

All deployment scripts in one place.

## Usage (Salam's Machine)

When notified of changes:
```bash
cd ~/inference_engine/automation
./deploy.sh
```

## Scripts

| Script | Purpose |
|--------|---------|
| `deploy.sh` | Pull latest code + restart services |
| `setup_instance.sh` | Initial server setup |
| `setup-runner.sh` | GitHub runner setup (optional) |
| `test_api.sh` | Test API endpoints |
| `run_worker.py` | Run Celery worker manually |
