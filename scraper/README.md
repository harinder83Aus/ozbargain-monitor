# OzBargain Scraper

The scraper component automatically collects deal data from OzBargain and stores it in PostgreSQL for the web application to display.

## How It Works

### Data Collection
- **RSS Feeds**: Scrapes OzBargain's RSS feeds every 6 hours
- **Main Feed**: `https://www.ozbargain.com.au/deals/feed`
- **Category Feeds**: Electronics, computing, gaming, mobile, etc.
- **Deal Extraction**: Parses titles, URLs, prices, stores, categories, votes

### Database Integration
- **Automatic Storage**: New deals saved to `deals` table
- **Duplicate Prevention**: URL-based uniqueness constraint
- **Deal Matching**: Automatically matches deals with active search terms
- **Activity Logging**: All scraping activity recorded in `scraping_logs` table

### Matching Algorithm
When new deals are found:
1. **Text Matching**: Compares deal titles/descriptions with search terms
2. **Scoring System**: 
   - Exact title match: 0.8 points
   - Partial word match: 0.3 points  
   - Description match: 0.4 points
   - Store name match: 0.5 points
3. **Threshold**: Only matches with score > 0.3 are stored
4. **Storage**: Matches saved to `search_matches` table

### Expired Deal Detection
- **Title Parsing**: Detects "(expired)" markers in deal titles
- **Date Extraction**: Parses expiry dates from deal text
- **Auto-Expiry**: Sets `expiry_date` for expired deals
- **Filtering**: Web app excludes expired deals from display

### Database Tables Used
- `deals` - Main deal storage
- `search_terms` - User-defined search criteria  
- `search_matches` - Links deals to matching search terms
- `scraping_logs` - Audit trail of scraper activity

### Health Monitoring
- **Health Endpoint**: `http://localhost:8000/health`
- **Status Endpoint**: `http://localhost:8000/status`
- **Database Connectivity**: Validates PostgreSQL connection
- **Error Logging**: Comprehensive error tracking and reporting

### Automation
- **Scheduled Runs**: Every 6 hours via Python `schedule` library
- **Jenkins Integration**: Can be triggered via CI/CD pipeline
- **Manual Execution**: Run `python main.py` for immediate scraping