# OzBargain Monitor - Complete Installation & Usage Guide

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running the Application](#running-the-application)
4. [Stopping the Application](#stopping-the-application)
5. [Uninstallation](#uninstallation)
6. [Usage Instructions](#usage-instructions)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## 🔧 Prerequisites

Before installing OzBargain Monitor, ensure you have the following installed on your Ubuntu system:

### Required Software
- **Docker**: Container platform
- **Docker Compose**: Multi-container management
- **Git**: Version control (for cloning the repository)
- **curl**: For health checks (usually pre-installed)

### System Requirements
- **OS**: Ubuntu 18.04 or later
- **RAM**: Minimum 2GB (4GB recommended)
- **Storage**: At least 1GB free space
- **Network**: Internet connection for scraping OzBargain

### Installing Prerequisites

#### 1. Install Docker
```bash
# Update package index
sudo apt update

# Install required packages
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
sudo apt update

# Install Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
# Or run: newgrp docker
```

#### 2. Install Docker Compose
Docker Compose v2 is now installed as a Docker plugin. If you have Docker Desktop or a recent Docker installation, it should already be available.

```bash
# Verify Docker Compose v2 installation
docker compose version

# If not available, install Docker Compose v2 plugin
sudo apt update
sudo apt install docker-compose-plugin
```

#### 3. Verify Docker Installation
```bash
# Check Docker version
docker --version

# Test Docker (should run without sudo)
docker run hello-world
```

---

## 🚀 Installation

### Method 1: Clone from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/ozbargain-monitor.git

# Navigate to project directory
cd ozbargain-monitor

# Make startup script executable
chmod +x start.sh

# Verify all files are present
ls -la
```

### Method 2: Download ZIP

```bash
# Download and extract ZIP file
wget https://github.com/yourusername/ozbargain-monitor/archive/main.zip
unzip main.zip
cd ozbargain-monitor-main

# Make startup script executable
chmod +x start.sh
```

### File Structure Verification
After installation, you should see:
```
ozbargain-monitor/
├── database/
│   └── schema.sql
├── scraper/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── database.py
│   └── ozbargain_scraper.py
├── web/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   ├── database.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── deals.html
│       ├── search_terms.html
│       ├── matched_deals.html
│       └── logs.html
├── docker-compose.yml
├── .env
├── start.sh
├── README.md
└── Guide.md
```

---

## ▶️ Running the Application

### Quick Start
```bash
# Navigate to project directory
cd ozbargain-monitor

# Run the startup script
./start.sh
```

### Manual Start
```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs
```

### Verification Steps

1. **Check Container Status**
```bash
docker compose ps
```
You should see:
- `ozbargain_db` (postgres) - Up
- `ozbargain_web` (web app) - Up  
- `ozbargain_scraper` (scraper) - Up

2. **Health Checks**
```bash
# Database health
docker compose exec postgres pg_isready -U ozbargain_user -d ozbargain_monitor

# Web application health
curl -f http://localhost:5000/health

# Scraper health
curl -f http://localhost:8000/health
```

3. **Access Web Interface**
- Open your browser and go to: http://localhost:5000
- You should see the OzBargain Monitor dashboard

---

## ⏹️ Stopping the Application

### Stop All Services
```bash
cd ozbargain-monitor
docker compose down
```

### Stop Individual Services
```bash
# Stop web application only
docker compose stop web

# Stop scraper only
docker compose stop scraper

# Stop database only
docker compose stop postgres
```

### Restart Services
```bash
# Restart all services
docker compose restart

# Restart individual service
docker compose restart web
```

---

## 🗑️ Uninstallation

### Complete Removal

1. **Stop and Remove Containers**
```bash
cd ozbargain-monitor
docker compose down -v
```

2. **Remove Docker Images**
```bash
# List project images
docker images | grep ozbargain

# Remove project images
docker rmi ozbargain-monitor_web ozbargain-monitor_scraper

# Remove PostgreSQL image (optional)
docker rmi postgres:15
```

3. **Remove Project Directory**
```bash
cd ..
rm -rf ozbargain-monitor
```

### Partial Removal (Keep Data)

If you want to keep your data but remove the application:
```bash
# Stop containers but keep volumes
docker compose down

# Remove project files but keep database volume
cd ..
rm -rf ozbargain-monitor
```

### Clean Docker System (Optional)
```bash
# Remove unused containers, networks, and images
docker system prune -a

# Remove unused volumes
docker volume prune
```

---

## 📖 Usage Instructions

### 1. Initial Setup

1. **Access the Application**
   - Open http://localhost:5000 in your browser

2. **Add Search Terms**
   - Go to "Search Terms" page
   - Click "Add Search Term"
   - Enter items you want to monitor (e.g., "iPhone", "laptop", "gaming headset")
   - Add optional descriptions
   - Click "Add Search Term"

### 2. Managing Search Terms

**Add New Search Terms:**
- Click "Add Search Term" button
- Enter the item name (e.g., "Nintendo Switch")
- Add description (optional)
- Click "Add Search Term"

**Activate/Deactivate Terms:**
- Use the toggle buttons to activate/deactivate search terms
- Deactivated terms won't match new deals

**Delete Terms:**
- Click "Delete" button next to unwanted terms
- Confirm deletion in the popup

### 3. Viewing Deals

**Dashboard:**
- Overview of system statistics
- Recent deals and matched deals
- Quick navigation to other pages

**All Deals:**
- Browse all scraped deals
- Pagination for easy navigation
- Deal details include price, store, votes, comments

**Matched Deals:**
- View only deals that match your search terms
- Filter by specific search terms
- Highlighted matching indicators

**Logs:**
- Monitor scraping activity
- View success/error rates
- Check scraping performance

### 4. Understanding Deal Information

Each deal shows:
- **Title**: Deal name and description
- **Price**: Current price (if available)
- **Store**: Where the deal is from
- **Category**: Deal category (electronics, gaming, etc.)
- **Votes**: Community upvotes/downvotes
- **Comments**: Number of comments
- **Age**: How long ago the deal was posted
- **Discount**: Percentage off (if available)

### 5. Monitoring System Health

**Health Checks:**
- Web app: http://localhost:5000/health
- Scraper: http://localhost:8000/health

**View Logs:**
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs scraper
docker-compose logs postgres
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Error**: "Port 5000 is already allocated"
**Solution**:
```bash
# Find process using port 5000
sudo netstat -tlnp | grep :5000

# Kill the process (replace PID with actual process ID)
sudo kill -9 PID

# Or change port in docker-compose.yml
```

#### 2. Database Connection Failed
**Error**: "Database connection failed"
**Solution**:
```bash
# Check if PostgreSQL container is running
docker compose ps

# Check database logs
docker compose logs postgres

# Restart database
docker compose restart postgres

# Wait for database to be ready
docker compose exec postgres pg_isready -U ozbargain_user -d ozbargain_monitor
```

#### 3. No Deals Appearing
**Possible Causes**:
- Scraper hasn't run yet (runs every 6 hours)
- Network connectivity issues
- OzBargain RSS feed temporarily unavailable

**Solution**:
```bash
# Check scraper logs
docker compose logs scraper

# Check scraper health
curl http://localhost:8000/health

# Manually trigger scraping (restart scraper)
docker compose restart scraper
```

#### 4. Web Interface Not Loading
**Error**: "This site can't be reached"
**Solution**:
```bash
# Check if web container is running
docker compose ps

# Check web application logs
docker compose logs web

# Restart web application
docker compose restart web

# Check if port is accessible
curl http://localhost:5000/health
```

#### 5. Docker Permission Denied
**Error**: "permission denied while trying to connect to Docker daemon"
**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or run:
newgrp docker

# Verify
docker run hello-world
```

#### 6. Out of Disk Space
**Error**: "No space left on device"
**Solution**:
```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune

# Check disk usage
df -h
```

### Log Analysis

#### Web Application Logs
```bash
# View web logs
docker compose logs web

# Common log messages:
# - "Database connection established" (Good)
# - "Error loading deals" (Check database)
# - "Health check passed" (Good)
```

#### Scraper Logs
```bash
# View scraper logs
docker compose logs scraper

# Common log messages:
# - "Scraping completed: X new, Y updated" (Good)
# - "Error scraping RSS feed" (Network issue)
# - "Database connection failed" (Database issue)
```

#### Database Logs
```bash
# View database logs
docker compose logs postgres

# Common log messages:
# - "database system is ready to accept connections" (Good)
# - "connection authorized" (Good)
# - "FATAL: database does not exist" (Setup issue)
```

---

## ⚙️ Advanced Configuration

### Environment Variables

Edit `.env` file to customize:

```bash
# Database Configuration
POSTGRES_DB=ozbargain_monitor
POSTGRES_USER=ozbargain_user
POSTGRES_PASSWORD=change_this_password

# Scraper Configuration
SCRAPE_INTERVAL=6  # Hours between scrapes
RSS_FEED_URL=https://www.ozbargain.com.au/deals/feed

# Web App Configuration
FLASK_SECRET_KEY=your-secret-key-here

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Custom Scraping Intervals

To change scraping frequency:
```bash
# Edit .env file
SCRAPE_INTERVAL=3  # Scrape every 3 hours instead of 6

# Restart scraper
docker compose restart scraper
```

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U ozbargain_user ozbargain_monitor > backup.sql

# Restore backup
docker compose exec -T postgres psql -U ozbargain_user -d ozbargain_monitor < backup.sql
```

### Performance Tuning

For high-volume monitoring:
```bash
# Edit docker-compose.yml to add resource limits
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### SSL/HTTPS Setup

For production use with SSL:
1. Obtain SSL certificates
2. Configure nginx reverse proxy
3. Update port mappings in docker-compose.yml

### Monitoring and Alerts

Set up monitoring:
```bash
# Add health check monitoring
while true; do
  curl -f http://localhost:5000/health || echo "Web app down!"
  curl -f http://localhost:8000/health || echo "Scraper down!"
  sleep 60
done
```

---

## 🆘 Getting Help

### Support Resources

1. **GitHub Issues**: Report bugs and request features
2. **Documentation**: Check README.md for additional information
3. **Logs**: Always check logs first for error messages

### Reporting Issues

When reporting issues, please include:
- Operating system and version
- Docker and Docker Compose versions
- Error messages from logs
- Steps to reproduce the issue

### Contributing

To contribute to the project:
1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Submit a pull request

---

## 📝 Changelog

### Version 1.0.0
- Initial release
- Basic deal monitoring and matching
- Web interface for management
- Docker containerization
- PostgreSQL database integration

---

This guide should help you successfully install, run, and manage your OzBargain Monitor application. For additional help, please refer to the project's GitHub repository or create an issue.