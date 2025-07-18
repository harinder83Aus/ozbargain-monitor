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