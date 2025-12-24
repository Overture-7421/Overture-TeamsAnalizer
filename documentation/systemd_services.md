# Systemd Services Configuration

This guide explains how to configure and manage the systemd services for running Overture Teams Analyzer on Linux.

## Overview

Two systemd services are available:

| Service | Description | Default State |
|---------|-------------|---------------|
| `overture-app.service` | Streamlit web interface | Enabled on install |
| `overture-hid.service` | HID barcode interceptor | Disabled (conditional) |

## Installation Script

The `scripts/install_services.sh` script manages both services.

### Install Services

```bash
cd /path/to/Overture-TeamsAnalizer
sudo ./scripts/install_services.sh --install
```

This will:
1. Check dependencies
2. Create data directory
3. Install both service files
4. Enable and start the app service
5. Leave HID service disabled

### Script Options

| Option | Description |
|--------|-------------|
| `--install` | Install and start services |
| `--uninstall` | Stop and remove services |
| `--status` | Show service status |
| `--enable-hid` | Enable HID interceptor service |
| `--disable-hid` | Disable HID interceptor service |
| `--help` | Show help message |

## Service Files

### overture-app.service

Located at `/etc/systemd/system/overture-app.service`:

```ini
[Unit]
Description=Overture Teams Analyzer - Streamlit Web Interface
Documentation=https://github.com/Overture-7421/Overture-TeamsAnalizer
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=<your-user>
Group=<your-group>
WorkingDirectory=/path/to/Overture-TeamsAnalizer
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/path/to/Overture-TeamsAnalizer/lib"
ExecStart=/usr/local/bin/streamlit run lib/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-app

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/path/to/Overture-TeamsAnalizer/data

[Install]
WantedBy=multi-user.target
```

### overture-hid.service

Located at `/etc/systemd/system/overture-hid.service`:

```ini
[Unit]
Description=Overture Teams Analyzer - HID Barcode/QR Scanner Interceptor
Documentation=https://github.com/Overture-7421/Overture-TeamsAnalizer
After=local-fs.target
ConditionPathExists=/path/to/lib/headless_interceptor.py
ConditionPathExists=/path/to/lib/columnsConfig.json

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/Overture-TeamsAnalizer
Environment="PYTHONPATH=/path/to/lib"
ExecStart=/usr/bin/python3 lib/headless_interceptor.py --config lib/columnsConfig.json --output data/default_scouting.csv
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=overture-hid

[Install]
WantedBy=multi-user.target
```

## Manual Service Management

### Start/Stop/Restart

```bash
# App service
sudo systemctl start overture-app
sudo systemctl stop overture-app
sudo systemctl restart overture-app

# HID service
sudo systemctl start overture-hid
sudo systemctl stop overture-hid
sudo systemctl restart overture-hid
```

### Enable/Disable Autostart

```bash
# Enable autostart
sudo systemctl enable overture-app
sudo systemctl enable overture-hid

# Disable autostart
sudo systemctl disable overture-app
sudo systemctl disable overture-hid
```

### Check Status

```bash
sudo systemctl status overture-app
sudo systemctl status overture-hid
```

### View Logs

```bash
# Real-time logs
journalctl -u overture-app -f
journalctl -u overture-hid -f

# Last 100 lines
journalctl -u overture-app -n 100

# Since boot
journalctl -u overture-hid -b

# With timestamps
journalctl -u overture-app --since "1 hour ago"
```

## Custom Configuration

### Custom Python Path

If using a virtual environment:

```bash
# Before running install script
export PYTHON_PATH=/home/user/overture-env/bin/python3
export STREAMLIT_PATH=/home/user/overture-env/bin/streamlit
sudo -E ./scripts/install_services.sh --install
```

### Custom Port

Edit the service file:

```bash
sudo systemctl edit overture-app --full
```

Change the ExecStart line:
```ini
ExecStart=/usr/local/bin/streamlit run lib/streamlit_app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart overture-app
```

### Running Multiple Instances

Create additional service files:

```bash
sudo cp /etc/systemd/system/overture-app.service /etc/systemd/system/overture-app-2.service
sudo nano /etc/systemd/system/overture-app-2.service
# Change port to 8502
sudo systemctl daemon-reload
sudo systemctl enable overture-app-2
sudo systemctl start overture-app-2
```

## Security Notes

### HID Service Permissions

The HID service runs as root to access `/dev/input/*` devices. For enhanced security:

1. Create a dedicated service user
2. Add udev rules for specific devices
3. Use capability bounding

Example udev rule:
```bash
echo 'SUBSYSTEM=="input", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="c141", MODE="0660", GROUP="input"' | \
    sudo tee /etc/udev/rules.d/99-scanner.rules
sudo udevadm control --reload-rules
```

Then modify service to run as non-root user in input group.

### App Service Hardening

The app service includes security hardening:

- `NoNewPrivileges=true` - Prevent privilege escalation
- `PrivateTmp=true` - Private /tmp directory
- `ProtectSystem=strict` - Read-only file system
- `ProtectHome=read-only` - Read-only home directories
- `ReadWritePaths=...` - Explicit write access to data directory

## Troubleshooting

### Service Fails to Start

```bash
# Check detailed error
sudo systemctl status overture-app
journalctl -u overture-app -n 50

# Common issues:
# 1. Wrong path in ExecStart
# 2. Missing dependencies
# 3. Permission issues
```

### Permission Denied Errors

```bash
# Check file ownership
ls -la /path/to/Overture-TeamsAnalizer/

# Fix ownership
sudo chown -R $USER:$USER /path/to/Overture-TeamsAnalizer/

# Check data directory
ls -la /path/to/Overture-TeamsAnalizer/data/
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8501

# Kill process
sudo kill <PID>

# Or use different port
sudo systemctl edit overture-app --full
# Change port number
```

### Service Keeps Restarting

```bash
# Check restart settings
sudo systemctl show overture-app | grep Restart

# Increase restart delay if needed
sudo systemctl edit overture-app
# Add: RestartSec=30
```
