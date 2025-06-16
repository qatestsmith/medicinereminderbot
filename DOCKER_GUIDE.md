# Docker Guide for Medicine Reminder Bot

## Table of Contents
- [Docker Theory Overview](#docker-theory-overview)
- [Dockerfile Explained](#dockerfile-explained)
- [Docker Layer Caching](#docker-layer-caching)
- [Build Process](#build-process)
- [Why This Design](#why-this-design)
- [Common Docker Commands](#common-docker-commands)

---

## Docker Theory Overview

### What is Docker?
Docker is a **containerization platform** that packages applications with all their dependencies into lightweight, portable containers.

```
Traditional Setup:           Docker Container:
┌─────────────────┐         ┌─────────────────┐
│   Your App      │         │ ┌─────────────┐ │
│                 │         │ │  Your App   │ │
├─────────────────┤         │ ├─────────────┤ │
│ Python 3.13     │         │ │ Python 3.11 │ │
│ Dependencies    │   VS    │ │ Dependencies│ │
│ System Libs     │         │ │ System Libs │ │
├─────────────────┤         │ ├─────────────┤ │
│ Host OS         │         │ │ Container OS│ │
│ (Linux/Windows) │         │ └─────────────┘ │
└─────────────────┘         │   Docker Engine │
                            └─────────────────┘
```

### Key Benefits:
- **Consistency** - Same environment everywhere (dev, test, production)
- **Isolation** - App runs in its own space
- **Portability** - Runs on any system with Docker
- **Reproducibility** - Exact same setup every time

### What is a Dockerfile?
A **Dockerfile** is a text file with instructions to build a Docker image. It's like a recipe that tells Docker:
1. What base system to use
2. What software to install  
3. How to configure the environment
4. What files to copy
5. How to run the application

---

## Dockerfile Explained

Here's our complete Dockerfile with detailed explanations:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./

# Create necessary directories
RUN mkdir -p data logs backups

# Make bot.py executable
RUN chmod +x bot.py

# Create non-root user for security
RUN useradd -r -s /bin/false botuser && \
    chown -R botuser:botuser /app

USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('data/database.db').execute('SELECT 1')" || exit 1

# Run the bot
CMD ["python", "bot.py"]
```

### Line-by-Line Breakdown:

#### 1. Base Image
```dockerfile
FROM python:3.11-slim
```
- **`FROM`** - Starts with an existing image
- **`python:3.11-slim`** - Official Python 3.11 image (lightweight version)
- **Why 3.11?** - More stable than 3.13 for our telegram bot libraries

#### 2. Working Directory
```dockerfile
WORKDIR /app
```
- **Sets the default directory** inside container to `/app`
- All subsequent commands run from this directory
- Like doing `cd /app` permanently

#### 3. System Dependencies
```dockerfile
RUN apt-get update && apt-get install -y \
    sqlite3 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*
```
- **`RUN`** - Executes commands during image build
- **`apt-get update`** - Updates package list
- **`sqlite3`** - Database engine for our bot
- **`tzdata`** - Timezone data for proper time handling
- **`rm -rf /var/lib/apt/lists/*`** - Cleans up to reduce image size

#### 4. Timezone Setup
```dockerfile
ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```
- **`ENV`** - Sets environment variable
- **`TZ=Europe/Kiev`** - Default timezone for Ukraine
- **`ln -snf`** - Creates symbolic link for timezone
- **Why?** - Ensures reminders work in correct timezone

#### 5. Python Dependencies
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- **`COPY`** - Copies file from host to container
- **Copy requirements first** - Docker layer caching optimization
- **`pip install`** - Installs Python packages
- **`--no-cache-dir`** - Reduces image size

#### 6. Application Code
```dockerfile
COPY app/ ./
```
- **Copies entire app directory** to container
- **Done after pip install** - So code changes don't rebuild Python packages

#### 7. Directory Creation
```dockerfile
RUN mkdir -p data logs backups
```
- **Creates necessary directories** for bot operation
- **`-p`** - Creates parent directories if needed

#### 8. Permissions
```dockerfile
RUN chmod +x bot.py
```
- **Makes bot.py executable** inside container

#### 9. Security
```dockerfile
RUN useradd -r -s /bin/false botuser && \
    chown -R botuser:botuser /app
USER botuser
```
- **`useradd -r`** - Creates system user (non-login)
- **`-s /bin/false`** - No shell access for security
- **`chown -R`** - Gives ownership of /app to botuser
- **`USER botuser`** - Switches to non-root user
- **Why?** - Security best practice (don't run as root)

#### 10. Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('data/database.db').execute('SELECT 1')" || exit 1
```
- **`HEALTHCHECK`** - Monitors container health
- **`--interval=30s`** - Check every 30 seconds
- **`--timeout=10s`** - Fail if check takes >10 seconds
- **`--retries=3`** - Try 3 times before marking unhealthy
- **The check** - Tries to connect to database
- **Why?** - Docker can restart unhealthy containers

#### 11. Run Command
```dockerfile
CMD ["python", "bot.py"]
```
- **`CMD`** - Default command when container starts
- **JSON format** - Recommended for proper signal handling
- **Runs the main bot** when container starts

---

## Docker Layer Caching

Docker builds images in **layers**. Each instruction creates a new layer:

```
Layer 7: CMD ["python", "bot.py"]           ← Changes frequently
Layer 6: COPY app/ ./                       ← Changes when code changes
Layer 5: RUN pip install...                 ← Only changes when requirements change
Layer 4: COPY requirements.txt .            ← Only changes when requirements change
Layer 3: RUN apt-get install...             ← Rarely changes
Layer 2: WORKDIR /app                       ← Never changes
Layer 1: FROM python:3.11-slim              ← Never changes
```

**Smart ordering:** Requirements copied before app code, so code changes don't trigger pip reinstall.

### Caching Benefits:
- **Faster builds** - Only rebuilds changed layers
- **Efficient storage** - Shared layers between images
- **Quick iteration** - Code changes don't rebuild everything

---

## Build Process

When you run `docker-compose build`:

1. **Reads Dockerfile** line by line
2. **Creates layers** for each instruction
3. **Caches layers** that haven't changed
4. **Only rebuilds** changed layers and everything after
5. **Tags final image** for use

### Build Flow Example:
```bash
# First build - everything is new
Step 1/11 : FROM python:3.11-slim          # Downloads base image
Step 2/11 : WORKDIR /app                   # Creates layer
Step 3/11 : RUN apt-get update...          # Installs system packages
Step 4/11 : ENV TZ=Europe/Kiev             # Sets timezone
Step 5/11 : COPY requirements.txt .        # Copies requirements
Step 6/11 : RUN pip install...             # Installs Python packages
Step 7/11 : COPY app/ ./                   # Copies application code
Step 8/11 : RUN mkdir -p data logs...      # Creates directories
Step 9/11 : RUN chmod +x bot.py            # Sets permissions
Step 10/11: RUN useradd -r...               # Creates user
Step 11/11: USER botuser                   # Switches user

# Second build (only code changed)
Step 1/6 : FROM python:3.11-slim          # CACHED
Step 2/6 : WORKDIR /app                   # CACHED
Step 3/6 : RUN apt-get update...          # CACHED
Step 4/6 : ENV TZ=Europe/Kiev             # CACHED
Step 5/6 : COPY requirements.txt .        # CACHED
Step 6/6 : RUN pip install...             # CACHED
Step 7/6 : COPY app/ ./                   # REBUILT (code changed)
Step 8/6 : RUN mkdir -p data logs...      # REBUILT
Step 9/6 : RUN chmod +x bot.py            # REBUILT
Step 10/6: RUN useradd -r...               # REBUILT
Step 11/6: USER botuser                   # REBUILT
```

---

## Why This Design?

### Optimized for Your Bot:
- **Python 3.11** - Stable for telegram libraries
- **Slim base** - Smaller image size (~150MB vs ~1GB full)
- **SQLite included** - For your database
- **Timezone aware** - For accurate reminders
- **Security hardened** - Non-root user
- **Health monitoring** - Auto-restart if unhealthy
- **Layer optimized** - Fast rebuilds during development

### Production Ready:
- **Reproducible builds** - Same result every time
- **Isolated environment** - Won't interfere with host
- **Easy deployment** - Works on any Docker host
- **Resource limited** - Won't consume unlimited resources
- **Logging integration** - Works with Docker logging drivers
- **Signal handling** - Proper shutdown on container stop

### Security Features:
- **Non-root execution** - Reduces attack surface
- **Minimal base image** - Fewer potential vulnerabilities
- **No shell access** - Bot user can't login
- **Isolated filesystem** - Changes don't affect host

---

## Common Docker Commands

### Building and Running:
```bash
# Build the image
docker-compose build

# Run the container
docker-compose up

# Run in background
docker-compose up -d

# Stop the container
docker-compose stop

# Remove container and image
docker-compose down --rmi all
```

### Debugging and Monitoring:
```bash
# View logs
docker-compose logs -f

# Execute command in running container
docker-compose exec medication-bot bash

# Check container status
docker-compose ps

# View resource usage
docker stats

# Inspect container details
docker inspect med-reminder-bot
```

### Maintenance:
```bash
# Create backup
docker exec med-reminder-bot python backup.py create

# View container health
docker inspect med-reminder-bot | grep Health -A 10

# Restart unhealthy container
docker-compose restart medication-bot

# Clean up unused images/containers
docker system prune
```

### Development Workflow:
```bash
# Make code changes
vim app/medicine_bot.py

# Rebuild and restart
docker-compose up --build

# Check logs for errors
docker-compose logs -f

# Test the bot
# (interact with bot on Telegram)

# Stop when done
docker-compose down
```

---

## Docker Compose Configuration

Our `docker-compose.yml` complements the Dockerfile:

```yaml
version: '3.8'

services:
  medication-bot:
    build: .                     # Build from Dockerfile
    container_name: med-reminder-bot
    restart: unless-stopped      # Auto-restart policy
    environment:
      - TZ=Europe/Kiev          # Timezone override
      - PYTHONUNBUFFERED=1      # Better logging
    volumes:                    # Persistent data
      - ./app/data:/app/data
      - ./app/config:/app/config
      - ./app/logs:/app/logs
      - ./app/backups:/app/backups
    mem_limit: 512m             # Resource limits
    cpus: 0.5
    logging:                    # Log rotation
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Key Features:
- **Persistent volumes** - Data survives container restarts
- **Resource limits** - Prevents resource exhaustion
- **Auto-restart** - Restarts on crash (but not manual stop)
- **Log rotation** - Prevents log files from growing too large

---

## Summary

This Docker setup provides:
- **Development efficiency** - Fast builds and iterations
- **Production reliability** - Stable, secure, monitored deployment
- **Operational simplicity** - Easy deployment and maintenance
- **Resource efficiency** - Optimized for Raspberry Pi constraints

The Dockerfile and docker-compose.yml work together to create a robust, production-ready deployment of your Telegram medication reminder bot! 🐳