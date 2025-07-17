#!/bin/bash

# OzBargain Monitor - Match Existing Deals Script
# This script matches existing deals with search terms using SQL

set -e

echo "🔍 OzBargain Monitor - Match Existing Deals"
echo "=" | tr '\n' '=' | head -c 50; echo

# Check if Docker container is running
if ! docker compose ps | grep -q "ozbargain_db.*Up"; then
    echo "❌ Error: Database container is not running"
    echo "   Please start the application first: docker compose up -d"
    exit 1
fi

# Get current statistics
echo "📊 Current Statistics:"
TOTAL_DEALS=$(docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -t -c "SELECT COUNT(*) FROM deals WHERE is_active = true;" | xargs)
TOTAL_SEARCH_TERMS=$(docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -t -c "SELECT COUNT(*) FROM search_terms WHERE is_active = true;" | xargs)
EXISTING_MATCHES=$(docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -t -c "SELECT COUNT(*) FROM search_matches;" | xargs)

echo "   • Total deals: $TOTAL_DEALS"
echo "   • Active search terms: $TOTAL_SEARCH_TERMS"
echo "   • Existing matches: $EXISTING_MATCHES"
echo

if [ "$TOTAL_SEARCH_TERMS" -eq 0 ]; then
    echo "⚠️  No active search terms found. Please add search terms first."
    exit 1
fi

if [ "$TOTAL_DEALS" -eq 0 ]; then
    echo "⚠️  No deals found in database. Please run the scraper first."
    exit 1
fi

# Show current search terms
echo "🎯 Current Search Terms:"
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "SELECT id, term, description FROM search_terms WHERE is_active = true ORDER BY id;"
echo

# Ask for confirmation
read -p "Do you want to match existing deals with your search terms? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled."
    exit 1
fi

echo "🚀 Starting matching process..."

# Create matches using SQL pattern matching
# This is a simplified version that matches terms in deal titles
docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
WITH deal_matches AS (
    SELECT 
        d.id as deal_id,
        st.id as search_term_id,
        CASE 
            WHEN LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' THEN 0.8
            WHEN LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' THEN 0.5
            WHEN LOWER(d.description) LIKE '%' || LOWER(st.term) || '%' THEN 0.4
            ELSE 0.0
        END as match_score
    FROM deals d
    CROSS JOIN search_terms st
    WHERE d.is_active = true 
    AND st.is_active = true
    AND LOWER(d.title) NOT LIKE '%expired%'
    AND LOWER(d.title) NOT LIKE '%(expired)%'
    AND (d.expiry_date IS NULL OR d.expiry_date > NOW())
    AND (
        LOWER(d.title) LIKE '%' || LOWER(st.term) || '%' OR
        LOWER(d.store) LIKE '%' || LOWER(st.term) || '%' OR
        LOWER(d.description) LIKE '%' || LOWER(st.term) || '%'
    )
)
INSERT INTO search_matches (deal_id, search_term_id, match_score, created_at)
SELECT deal_id, search_term_id, match_score, NOW()
FROM deal_matches
WHERE match_score > 0.3
AND NOT EXISTS (
    SELECT 1 FROM search_matches sm 
    WHERE sm.deal_id = deal_matches.deal_id 
    AND sm.search_term_id = deal_matches.search_term_id
);
"

# Get results
NEW_MATCHES=$(docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -t -c "SELECT COUNT(*) FROM search_matches;" | xargs)
MATCHES_FOUND=$((NEW_MATCHES - EXISTING_MATCHES))

echo "✅ Matching completed!"
echo "   • New matches found: $MATCHES_FOUND"
echo "   • Total matches now: $NEW_MATCHES"
echo

if [ "$MATCHES_FOUND" -gt 0 ]; then
    echo "🎯 Sample of matched deals:"
    docker compose exec postgres psql -U ozbargain_user -d ozbargain_monitor -c "
    SELECT 
        st.term as search_term,
        d.title as deal_title,
        d.store,
        ROUND(sm.match_score::numeric, 2) as score
    FROM search_matches sm
    JOIN deals d ON sm.deal_id = d.id
    JOIN search_terms st ON sm.search_term_id = st.id
    ORDER BY sm.created_at DESC, sm.match_score DESC
    LIMIT 10;
    "
    echo
fi

echo "🎉 You can now view your matched deals in the web interface!"
echo "   Visit: http://localhost:5000/matched-deals"