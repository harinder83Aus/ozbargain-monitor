#!/bin/bash

# OzBargain Monitor Startup Script

set -e

echo "🚀 Starting OzBargain Monitor..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Create directories if they don't exist
mkdir -p database logs

# Set executable permissions
chmod +x start.sh

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start containers
echo "🏗️ Building and starting containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check database
if docker-compose exec postgres pg_isready -U ozbargain_user -d ozbargain_monitor &> /dev/null; then
    echo "✅ Database is ready"
else
    echo "❌ Database health check failed"
fi

# Check web app
if curl -f http://localhost:5000/health &> /dev/null; then
    echo "✅ Web application is ready"
else
    echo "❌ Web application health check failed"
fi

# Check scraper
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Scraper service is ready"
else
    echo "❌ Scraper service health check failed"
fi

echo ""
echo "🎉 OzBargain Monitor is now running!"
echo ""
echo "📊 Web Dashboard: http://localhost:5000"
echo "🔧 Scraper Status: http://localhost:8000/status"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose logs"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo ""
echo "💡 Next steps:"
echo "   1. Open http://localhost:5000 in your browser"
echo "   2. Go to 'Search Terms' page to add items you want to monitor"
echo "   3. Wait for the scraper to find matching deals (runs every 6 hours)"
echo ""