import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
from database import DatabaseManager, Deal, SearchTerm, SearchMatch, ScrapingLog

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')

# Initialize database manager
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

db_manager = DatabaseManager(database_url)

@app.route('/')
def index():
    """Homepage - Summary of recent deals"""
    try:
        # Get recent deals
        recent_deals = db_manager.get_recent_deals(limit=20)
        
        # Get matched deals
        matched_deals = db_manager.get_matched_deals(limit=20)
        
        # Get statistics
        stats = db_manager.get_statistics()
        
        return render_template('index.html', 
                             recent_deals=recent_deals,
                             matched_deals=matched_deals,
                             stats=stats)
    except Exception as e:
        logger.error(f"Error loading homepage: {e}")
        flash(f"Error loading deals: {str(e)}", 'error')
        return render_template('index.html', recent_deals=[], matched_deals=[], stats={})

@app.route('/deals')
def deals():
    """All deals page with optional store filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        store_filter = request.args.get('store', '').strip()
        per_page = 20
        
        # Get available stores for the filter dropdown
        available_stores = db_manager.get_available_stores(min_deals=2)
        
        # Get deals with optional store filter
        if store_filter:
            deals = db_manager.get_recent_deals(limit=per_page * page, store_filter=store_filter)
        else:
            deals = db_manager.get_recent_deals(limit=per_page * page)
        
        # Pagination logic (simple for now)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_deals = deals[start_idx:end_idx]
        
        has_next = len(deals) > end_idx
        has_prev = page > 1
        
        return render_template('deals.html', 
                             deals=page_deals,
                             page=page,
                             has_next=has_next,
                             has_prev=has_prev,
                             available_stores=available_stores,
                             current_store_filter=store_filter)
    except Exception as e:
        logger.error(f"Error loading deals page: {e}")
        flash(f"Error loading deals: {str(e)}", 'error')
        return render_template('deals.html', deals=[], page=1, has_next=False, has_prev=False, available_stores=[], current_store_filter='')

@app.route('/search-terms')
def search_terms():
    """Search terms management page"""
    try:
        search_terms = db_manager.get_search_terms(include_inactive=True)
        return render_template('search_terms.html', search_terms=search_terms)
    except Exception as e:
        logger.error(f"Error loading search terms page: {e}")
        flash(f"Error loading search terms: {str(e)}", 'error')
        return render_template('search_terms.html', search_terms=[])

@app.route('/search-terms/add', methods=['POST'])
def add_search_term():
    """Add a new search term"""
    try:
        term = request.form.get('term', '').strip()
        description = request.form.get('description', '').strip()
        
        if not term:
            flash('Search term cannot be empty', 'error')
            return redirect(url_for('search_terms'))
        
        db_manager.add_search_term(term, description if description else None)
        flash(f'Search term "{term}" added successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error adding search term: {e}")
        flash(f"Error adding search term: {str(e)}", 'error')
    
    return redirect(url_for('search_terms'))

@app.route('/search-terms/<int:term_id>/toggle', methods=['POST'])
def toggle_search_term(term_id):
    """Toggle search term active status"""
    try:
        is_active = request.form.get('is_active') == 'true'
        
        if not is_active:
            # Deactivating - purge existing matches
            purged_count = db_manager.purge_search_matches(term_id)
            db_manager.update_search_term(term_id, is_active=is_active)
            flash(f'Search term deactivated and {purged_count} matched deals purged', 'success')
        else:
            # Reactivating - just update status, don't purge anything
            db_manager.update_search_term(term_id, is_active=is_active)
            flash('Search term reactivated successfully - new deals will be matched going forward', 'success')
        
    except Exception as e:
        logger.error(f"Error toggling search term: {e}")
        flash(f"Error updating search term: {str(e)}", 'error')
    
    return redirect(url_for('search_terms'))

@app.route('/search-terms/<int:term_id>/delete', methods=['POST'])
def delete_search_term(term_id):
    """Delete a search term"""
    try:
        # Count existing matches before deleting
        purged_count = db_manager.purge_search_matches(term_id)
        success = db_manager.delete_search_term(term_id)
        if success:
            flash(f'Search term deleted and {purged_count} matched deals purged', 'success')
        else:
            flash('Search term not found', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting search term: {e}")
        flash(f"Error deleting search term: {str(e)}", 'error')
    
    return redirect(url_for('search_terms'))

@app.route('/matched-deals')
def matched_deals():
    """Matched deals page"""
    try:
        search_term_id = request.args.get('search_term_id', type=int)
        
        # Get matched deals
        matched_deals = db_manager.get_matched_deals(search_term_id=search_term_id, limit=50)
        
        # Get search terms for filter dropdown
        search_terms = db_manager.get_search_terms()
        
        return render_template('matched_deals.html', 
                             deals=matched_deals,
                             search_terms=search_terms,
                             selected_search_term_id=search_term_id)
    except Exception as e:
        logger.error(f"Error loading matched deals page: {e}")
        flash(f"Error loading matched deals: {str(e)}", 'error')
        return render_template('matched_deals.html', deals=[], search_terms=[], selected_search_term_id=None)

@app.route('/logs')
def logs():
    """Scraping logs page"""
    try:
        logs = db_manager.get_scraping_logs(limit=50)
        return render_template('logs.html', logs=logs)
    except Exception as e:
        logger.error(f"Error loading logs page: {e}")
        flash(f"Error loading logs: {str(e)}", 'error')
        return render_template('logs.html', logs=[])

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    try:
        stats = db_manager.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        stats = db_manager.get_statistics()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': stats
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

# Template filters
@app.template_filter('datetime')
def datetime_format(value):
    """Format datetime for display"""
    if value is None:
        return ''
    return value.strftime('%Y-%m-%d %H:%M:%S')

@app.template_filter('timeago')
def timeago_format(value):
    """Format datetime as time ago"""
    if value is None:
        return ''
    
    now = datetime.utcnow()
    diff = now - value
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)