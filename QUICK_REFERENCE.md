# OzBargain Monitor - Quick Reference

## 🚀 Quick Start
```bash
git clone https://github.com/harinder83Aus/ozbargain-monitor.git
cd ozbargain-monitor
./start.sh
```
→ Open http://localhost:5000

## 📋 Common Commands

### Installation & Setup
```bash
# Clone repository
git clone https://github.com/harinder83Aus/ozbargain-monitor.git
cd ozbargain-monitor

# Start application
./start.sh
```

### Running the Application
```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs
```

### Stopping the Application
```bash
# Stop all services
docker compose down

# Stop specific service
docker compose stop web
```

### Troubleshooting
```bash
# Check service health
curl http://localhost:5000/health
curl http://localhost:8000/health

# View specific service logs
docker compose logs web
docker compose logs scraper
docker compose logs postgres

# Restart services
docker compose restart
```

### Database Operations
```bash
# Connect to database
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor

# Backup database
docker compose exec postgres pg_dump -U ozbargain_user ozbargain_monitor > backup.sql

# Restore database
docker compose exec -T postgres psql -U ozbargain_user -d ozbargain_monitor < backup.sql
```

### Data Cleanup
```bash
# Setup automatic weekly cleanup
./setup_cron.sh

# Manual cleanup (any day)
./manual_cleanup.sh

# View cleanup logs
tail -f /var/log/ozbargain_cleanup.log

# Check cron jobs
crontab -l
```

## 🔗 Important URLs
- **Web Interface**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **Scraper Status**: http://localhost:8000/status
- **API Stats**: http://localhost:5000/api/stats

## 📁 Key Files
- `docker-compose.yml` - Service configuration
- `.env` - Environment variables
- `start.sh` - Startup script
- `Guide.md` - Detailed installation guide
- `README.md` - Project overview

## ⚡ One-Liners
```bash
# Quick health check
curl -s http://localhost:5000/health | jq

# Check all container status
docker compose ps --services --filter "status=running"

# View recent logs
docker compose logs --tail=50 --follow

# Clean restart
docker compose down && docker compose up -d

# Update from GitHub
git pull origin main && docker compose up -d --build
```

## 🆘 Emergency Commands
```bash
# Force stop all containers
docker compose kill

# Remove all containers and volumes
docker compose down -v

# Clean Docker system
docker system prune -a

# Check disk usage
docker system df
```

## 📊 Monitoring
```bash
# Container resource usage
docker stats

# Service logs in real-time
docker compose logs -f scraper

# Database connections
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "SELECT * FROM pg_stat_activity;"
```