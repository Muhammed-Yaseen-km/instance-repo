# Automation Scripts

## Setup (Run Once on Salam's Machine)

```bash
cd ~/inference_engine/automation
chmod +x setup-runner.sh
./setup-runner.sh
```

## What Gets Automated

After setup, every `git push` to main will:
1. Trigger GitHub Actions
2. Run directly on Salam's GPU machine
3. Pull latest code
4. Restart Docker services

Zero manual intervention needed.
