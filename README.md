# OzBargain Monitor

A web application that monitors OzBargain deals and matches them with your search terms every 6 hours.

## Features

- **Automated Deal Monitoring**: Scrapes OzBargain RSS feeds every 6 hours
- **Search Term Management**: Add items you want to monitor for deals
- **Deal Matching**: Automatically matches deals with your search terms
- **Web Dashboard**: View recent deals, matched deals, and statistics
- **Docker Deployment**: Easy deployment with Docker containers
- **PostgreSQL Database**: Stores deals, search terms, and matching data

## Architecture

- **Web App**: Flask application with Bootstrap UI
- **Scraper**: Python service that monitors OzBargain RSS feeds
- **Database**: PostgreSQL for data storage
- **Docker**: Multi-container setup with docker-compose

## Quick Start

1. **Clone and Setup**:
   ```bash
   cd /home/harry/ozbargain-monitor
   ```

2. **Configure Environment**:
   Edit `.env` file if needed (defaults should work)

3. **Start the Application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the Web App**:
   Open http://localhost:5000 in your browser

## Usage

### Adding Search Terms

1. Navigate to **Search Terms** page
2. Click **Add Search Term**
3. Enter the item you want to monitor (e.g., "iPhone", "laptop", "gaming headset")
4. Add an optional description
5. Click **Add Search Term**

### Viewing Deals

- **Dashboard**: Overview of recent deals and matched deals
- **All Deals**: Browse all scraped deals with pagination
- **Matched Deals**: View only deals that match your search terms
- **Logs**: Monitor scraping activity and performance

### Managing Search Terms

- **Activate/Deactivate**: Toggle search terms on/off
- **Delete**: Remove search terms you no longer need
- **Filter**: View matched deals by specific search terms

## Services

### Web Application (Port 5000)
- Flask web interface
- Deal management and viewing
- Search term configuration
- Statistics and logs

### Scraper Service (Port 8000)
- RSS feed monitoring
- Deal extraction and matching
- Scheduled scraping every 6 hours
- Health check endpoint

### Database (Port 5432)
- PostgreSQL database
- Stores deals, search terms, matches, and logs
- Automatic schema initialization

## API Endpoints

### Web Application
- `GET /` - Dashboard
- `GET /deals` - All deals
- `GET /matched-deals` - Matched deals
- `GET /search-terms` - Search terms management
- `GET /logs` - Scraping logs
- `GET /health` - Health check
- `GET /api/stats` - Statistics API

### Scraper Service
- `GET /health` - Health check
- `GET /status` - Scraper status and statistics

## Configuration

### Environment Variables (.env)
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `SCRAPE_INTERVAL`: Scraping interval in hours (default: 6)
- `RSS_FEED_URL`: OzBargain RSS feed URL
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

### Data Sources
- Main RSS feed: https://www.ozbargain.com.au/deals/feed
- Category feeds: https://www.ozbargain.com.au/cat/{category}/feed

## Database Schema

### Tables
- `deals`: Stores deal information
- `search_terms`: User-defined search terms
- `search_matches`: Links deals to matching search terms
- `scraping_logs`: Logs scraping activities

## Development

### Local Development
```bash
# Start only the database
docker-compose up -d postgres

# Run web app locally
cd web
pip install -r requirements.txt
python app.py

# Run scraper locally
cd scraper
pip install -r requirements.txt
python main.py
```

### Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs scraper
docker-compose logs postgres
```

### Database Access
```bash
# Connect to database
docker exec -it ozbargain_db psql -U ozbargain_user -d ozbargain_monitor
```

## Monitoring

- **Health Checks**: All services include health check endpoints
- **Logs**: Scraping activities are logged in the database
- **Statistics**: Dashboard shows deal counts and activity stats
- **Error Handling**: Failed scraping attempts are logged with error details

## Security Considerations

- Change default passwords in `.env` file
- Use HTTPS in production
- Implement rate limiting if needed
- Monitor scraping frequency to respect OzBargain's servers

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check if PostgreSQL container is running
   - Verify database credentials in `.env`

2. **No Deals Appearing**
   - Check scraper logs for errors
   - Verify RSS feed accessibility
   - Check scraper health endpoint

3. **Web App Not Loading**
   - Ensure port 5000 is not in use
   - Check web container logs

### Useful Commands
```bash
# Restart all services
docker-compose restart

# Rebuild containers
docker-compose build

# View container status
docker-compose ps

# Stop all services
docker-compose down
```

## License

This project is for educational purposes. Please respect OzBargain's terms of service and server resources.