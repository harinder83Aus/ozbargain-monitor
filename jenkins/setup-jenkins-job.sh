#!/bin/bash

# OzBargain Monitor - Jenkins Job Setup Script
# This script helps set up the Jenkins pipeline job for automated deployment

set -e

echo "🔧 OzBargain Monitor - Jenkins Job Setup"
echo "========================================"

# Configuration
JENKINS_URL="${JENKINS_URL:-http://localhost:8080}"
JOB_NAME="ozbargain-monitor-deploy"
PROJECT_DIR="/home/harry/ozbargain-monitor"

echo "📋 Configuration:"
echo "   Jenkins URL: $JENKINS_URL"
echo "   Job Name: $JOB_NAME"
echo "   Project Directory: $PROJECT_DIR"
echo ""

# Check if Jenkins CLI is available
if ! command -v jenkins-cli.jar &> /dev/null && [ ! -f "jenkins-cli.jar" ]; then
    echo "📥 Downloading Jenkins CLI..."
    wget -q "${JENKINS_URL}/jnlpJars/jenkins-cli.jar" -O jenkins-cli.jar
    echo "✅ Jenkins CLI downloaded"
else
    echo "✅ Jenkins CLI found"
fi

# Function to create job via CLI
create_job_via_cli() {
    echo "🚀 Creating Jenkins job via CLI..."
    
    # Check if Jenkins is accessible
    if ! curl -s "${JENKINS_URL}" > /dev/null; then
        echo "❌ Error: Cannot access Jenkins at ${JENKINS_URL}"
        echo "   Please ensure Jenkins is running and accessible"
        exit 1
    fi
    
    # Create or update the job
    if java -jar jenkins-cli.jar -s "${JENKINS_URL}" create-job "${JOB_NAME}" < job-config.xml 2>/dev/null; then
        echo "✅ Job '${JOB_NAME}' created successfully"
    elif java -jar jenkins-cli.jar -s "${JENKINS_URL}" update-job "${JOB_NAME}" < job-config.xml 2>/dev/null; then
        echo "✅ Job '${JOB_NAME}' updated successfully"
    else
        echo "❌ Failed to create/update job. You may need to:"
        echo "   1. Configure Jenkins authentication"
        echo "   2. Install required plugins"
        echo "   3. Create the job manually using the Web UI"
        return 1
    fi
}

# Function to provide manual setup instructions
manual_setup_instructions() {
    echo ""
    echo "📖 Manual Setup Instructions:"
    echo "============================="
    echo ""
    echo "1. 🌐 Open Jenkins Web UI:"
    echo "   ${JENKINS_URL}"
    echo ""
    echo "2. 📁 Create New Job:"
    echo "   - Click 'New Item'"
    echo "   - Enter job name: ${JOB_NAME}"
    echo "   - Select 'Pipeline'"
    echo "   - Click 'OK'"
    echo ""
    echo "3. ⚙️ Configure Pipeline:"
    echo "   - In 'Pipeline' section:"
    echo "   - Definition: 'Pipeline script from SCM'"
    echo "   - SCM: 'Git'"
    echo "   - Repository URL: your-git-repo-url"
    echo "   - Branch: */main"
    echo "   - Script Path: Jenkinsfile"
    echo ""
    echo "4. 🔧 Required Jenkins Plugins:"
    echo "   - Pipeline"
    echo "   - Git"
    echo "   - Docker Pipeline (optional)"
    echo "   - Timestamper"
    echo ""
    echo "5. 🚀 Run the Pipeline:"
    echo "   - Click 'Build Now'"
    echo "   - Monitor the build logs"
    echo ""
}

# Function to create a quick-run script
create_run_script() {
    cat > run-deployment.sh << 'EOF'
#!/bin/bash

# Quick deployment script - Alternative to Jenkins
# Run this script to perform the same steps as the Jenkins pipeline

set -e

echo "🚀 OzBargain Monitor - Manual Deployment"
echo "======================================="

# Check for changes
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Committing changes..."
    git add .
    git commit -m "Manual deployment - $(date '+%Y-%m-%d %H:%M:%S')"
    git push origin main
    echo "✅ Changes committed and pushed"
else
    echo "✅ No changes to commit"
fi

# Restart stack
echo "🔄 Restarting Docker stack..."
docker compose down
docker compose up -d

# Wait for services
echo "⏳ Waiting for services..."
sleep 30

# Run migrations
echo "🔧 Running migrations..."
docker compose exec -T web python /app/migrate.py

# Health checks
echo "🏥 Running health checks..."

# Check database
if docker compose exec -T postgres psql -U ozbargain_user -d ozbargain_monitor -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Database: Healthy"
else
    echo "❌ Database: Unhealthy"
fi

# Check web app
if curl -s http://localhost:5000/health > /dev/null; then
    echo "✅ Web App: Healthy"
else
    echo "❌ Web App: Unhealthy"
fi

# Check scraper
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Scraper: Healthy"
else
    echo "⚠️ Scraper: May still be starting"
fi

echo ""
echo "🎉 Deployment completed!"
echo "🌐 Access your application at: http://localhost:5000"
EOF

    chmod +x run-deployment.sh
    echo "✅ Created run-deployment.sh script for manual deployment"
}

# Main execution
echo "🔍 Checking Jenkins accessibility..."

if curl -s "${JENKINS_URL}" > /dev/null; then
    echo "✅ Jenkins is accessible"
    
    # Try to create job via CLI
    if create_job_via_cli; then
        echo ""
        echo "🎉 Jenkins job setup completed!"
        echo ""
        echo "🚀 To run the deployment pipeline:"
        echo "   1. Visit: ${JENKINS_URL}/job/${JOB_NAME}/"
        echo "   2. Click 'Build Now'"
        echo ""
        echo "📊 Pipeline Features:"
        echo "   ✅ Automatic git commit & push"
        echo "   ✅ Full Docker stack restart"
        echo "   ✅ Database migrations"
        echo "   ✅ Comprehensive health checks"
        echo "   ✅ Detailed status reporting"
    else
        manual_setup_instructions
    fi
else
    echo "⚠️ Jenkins not accessible at ${JENKINS_URL}"
    manual_setup_instructions
fi

# Always create the manual run script as backup
echo ""
echo "📦 Creating backup deployment script..."
create_run_script

echo ""
echo "✅ Setup completed!"
echo ""
echo "📁 Files created:"
echo "   - jenkins/job-config.xml (Jenkins job configuration)"
echo "   - jenkins/setup-jenkins-job.sh (this setup script)"
echo "   - run-deployment.sh (manual deployment alternative)"
echo "   - Jenkinsfile (pipeline definition)"
echo ""