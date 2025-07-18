# Jenkins CI/CD Pipeline for OzBargain Monitor

This directory contains the Jenkins pipeline configuration for automating the deployment workflow of the OzBargain Monitor application.

## 🎯 Pipeline Purpose

The Jenkins pipeline automates the complete development workflow:

1. **📝 Git Automation** - Commits pending changes and pushes to GitHub
2. **🔄 Stack Restart** - Stops and starts the entire Docker stack with fresh builds
3. **🏥 Health Checks** - Comprehensive testing of all services
4. **📊 Status Reporting** - Detailed deployment status and system information

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
cd /home/harry/ozbargain-monitor/jenkins
./setup-jenkins-job.sh
```

### Option 2: Manual Setup

1. **Access Jenkins**: Open http://localhost:8080
2. **Create Job**: New Item → Pipeline → Name: `ozbargain-monitor-deploy`
3. **Configure Pipeline**:
   - Definition: "Pipeline script from SCM"
   - SCM: Git
   - Repository URL: `https://github.com/harinder83Aus/ozbargain-monitor.git`
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`

## 📋 Required Jenkins Plugins

Ensure these plugins are installed:

- ✅ **Pipeline** - Core pipeline functionality
- ✅ **Git** - Git repository integration  
- ✅ **Timestamper** - Timestamps in build logs
- ✅ **Docker Pipeline** (optional) - Enhanced Docker support

## 🔧 Pipeline Stages

### 1. 🔍 Pre-deployment Checks
- Verifies Docker is running
- Checks for pending git changes
- Validates environment requirements

### 2. 📝 Git Commit & Push
- Commits all pending changes automatically
- Creates descriptive commit messages with timestamps
- Pushes changes to remote repository

### 3. 🛑 Stop Current Stack
- Gracefully stops all running containers
- Handles cases where stack is already stopped

### 4. 🧹 Cleanup Docker Resources
- Removes dangling images
- Cleans up build cache
- Optimizes disk space usage

### 5. 🚀 Deploy New Stack
- Builds and starts all containers
- Uses latest code changes
- Ensures fresh deployment

### 6. ⏳ Wait for Services
- Waits for database health checks
- Allows services to fully initialize
- Timeout protection (5 minutes)

### 7. 🔧 Run Database Migrations
- Executes pending database migrations
- Ensures schema is up to date
- Handles migration errors gracefully

### 8. 🏥 Health Checks (Parallel)
- **Database Health**: Direct PostgreSQL connection test
- **Web Application**: HTTP health endpoint check
- **Scraper Service**: API health endpoint verification
- **Container Status**: All containers running verification

### 9. 📊 System Status Report
- Container status summary
- Database statistics
- Recent migration history
- Disk usage information

## 🎮 How to Use

### Running the Pipeline

1. **Via Jenkins UI**:
   - Visit: http://localhost:8080/job/ozbargain-monitor-deploy/
   - Click "Build Now"
   - Monitor progress in real-time

2. **Via Jenkins CLI** (if configured):
   ```bash
   java -jar jenkins-cli.jar -s http://localhost:8080 build ozbargain-monitor-deploy
   ```

3. **Manual Alternative** (backup):
   ```bash
   cd /home/harry/ozbargain-monitor
   ./run-deployment.sh
   ```

### When to Run

- ✅ After making code changes
- ✅ When testing new features
- ✅ Before demonstrating the application
- ✅ After database schema changes
- ✅ Weekly maintenance deployments

## 📊 Pipeline Output

### Success Output
```
🎉 ===== DEPLOYMENT SUCCESSFUL =====
✅ Git changes committed and pushed
✅ Docker stack restarted successfully  
✅ All health checks passed
✅ System is ready for use

🌐 Access your application at:
   - Web Interface: http://localhost:5000
   - Scraper API: http://localhost:8000
   - Database: localhost:5432
```

### Health Check Details
- Database response time and connection status
- Web application HTTP status codes
- Scraper service availability
- Container resource usage
- Migration execution results

## 🔧 Troubleshooting

### Common Issues

**Pipeline Fails at Git Stage**:
- Check git repository permissions
- Verify Jenkins has access to GitHub
- Ensure git credentials are configured

**Docker Build Failures**:
- Check disk space: `docker system df`
- Clean up resources: `docker system prune`
- Verify Docker daemon is running

**Health Check Failures**:
- Check service logs: `docker compose logs [service]`
- Verify port availability (5000, 8000, 5432)
- Ensure database has proper data

**Migration Errors**:
- Check database connectivity
- Review migration files in `/database/migrations/`
- Verify schema_migrations table exists

### Manual Recovery

If pipeline fails, you can recover manually:

```bash
# Stop everything
docker compose down

# Clean up
docker system prune -f

# Restart manually
docker compose up -d

# Check status
docker compose ps
curl http://localhost:5000/health
```

## 📁 File Structure

```
jenkins/
├── README.md              # This documentation
├── job-config.xml         # Jenkins job XML configuration
├── setup-jenkins-job.sh   # Automated setup script
└── ../Jenkinsfile         # Pipeline definition (root directory)
└── ../run-deployment.sh   # Manual deployment alternative
```

## ⚡ Performance Notes

- **Typical Runtime**: 5-10 minutes
- **Parallel Execution**: Health checks run simultaneously
- **Timeout Protection**: 30-minute maximum pipeline duration
- **Resource Cleanup**: Automatic Docker cache management
- **Retry Logic**: Failed stages retry automatically

## 🔒 Security Considerations

- Git credentials should use SSH keys or personal access tokens
- Jenkins should run with limited user permissions
- Database credentials are managed via environment variables
- Container networks are isolated from host system

## 🎯 Benefits

✅ **Eliminates Manual Steps** - No more manual git commits or Docker restarts
✅ **Consistent Deployments** - Same process every time
✅ **Error Detection** - Comprehensive health checks catch issues early
✅ **Audit Trail** - Complete build history and logs
✅ **Time Savings** - Automated workflow saves 10+ minutes per deployment
✅ **Reliability** - Tested pipeline reduces deployment errors

---

**Need Help?** Check the Jenkins build logs for detailed error information, or run the manual deployment script as a fallback.