#!/bin/bash
set -e

echo "🔄 Starting OzBargain Monitor Web Application"

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
python -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

url = urlparse(os.environ['DATABASE_URL'])
max_attempts = 30
for attempt in range(max_attempts):
    try:
        conn = psycopg2.connect(
            host=url.hostname,
            port=url.port,
            user=url.username, 
            password=url.password,
            database=url.path[1:]
        )
        conn.close()
        print('✅ Database is ready!')
        break
    except psycopg2.OperationalError:
        if attempt < max_attempts - 1:
            print(f'Database not ready, retrying... ({attempt + 1}/{max_attempts})')
            time.sleep(2)
        else:
            print('❌ Database connection failed')
            exit(1)
"

# Run database migrations
echo "🔄 Running database migrations..."
python /app/migrate.py

# Start the web application
echo "🚀 Starting Flask application..."
exec python app.py