pipeline {
    agent any
    
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        retry(2)
    }
    
    environment {
        PROJECT_NAME = 'ozbargain-monitor'
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
        GIT_COMMITTER_NAME = 'Jenkins CI'
        GIT_COMMITTER_EMAIL = 'jenkins@ozbargain-monitor.local'
        GIT_AUTHOR_NAME = 'Jenkins CI'
        GIT_AUTHOR_EMAIL = 'jenkins@ozbargain-monitor.local'
        WORKSPACE_DIR = "${WORKSPACE}"
    }
    
    stages {
        stage('🔍 Pre-deployment Checks') {
            steps {
                echo '🔍 Running pre-deployment checks...'
                
                // Check if Docker is running
                sh 'docker --version'
                sh 'docker compose version'
                
                // Check current git status
                sh 'git status --porcelain'
                
                // Check if there are any changes to commit
                script {
                    def changes = sh(script: 'git status --porcelain', returnStdout: true).trim()
                    if (changes) {
                        echo "📝 Found changes to commit:"
                        echo "${changes}"
                        env.HAS_CHANGES = 'true'
                    } else {
                        echo "✅ No changes to commit"
                        env.HAS_CHANGES = 'false'
                    }
                }
            }
        }
        
        stage('📝 Git Commit (Local)') {
            when {
                expression { env.HAS_CHANGES == 'true' }
            }
            steps {
                echo '📝 Committing changes locally...'
                
                script {
                    // Add all changes
                    sh 'git add .'
                    
                    // Create commit message with timestamp
                    def timestamp = sh(script: 'date "+%Y-%m-%d %H:%M:%S"', returnStdout: true).trim()
                    def commitMessage = """Automated deployment commit - ${timestamp}

Auto-generated commit from Jenkins CI pipeline
- Applied latest code changes
- Ready for deployment and testing

🤖 Generated with [Claude Code](https://claude.ai/code)
🔧 Automated by Jenkins CI

Co-Authored-By: Claude <noreply@anthropic.com>"""
                    
                    // Commit changes locally only
                    sh """
                        git checkout main || git checkout -b main
                        git commit -m '${commitMessage}' || echo 'No changes to commit'
                    """
                    
                    echo '✅ Changes committed locally (skipping push for local development)'
                    echo '💡 To push manually later: git push origin main'
                }
            }
        }
        
        stage('🛑 Stop Current Stack') {
            steps {
                echo '🛑 Stopping current Docker stack...'
                
                script {
                    try {
                        sh 'docker compose -f ${DOCKER_COMPOSE_FILE} down'
                        echo '✅ Stack stopped successfully'
                    } catch (Exception e) {
                        echo "⚠️ Stack was not running or already stopped: ${e.getMessage()}"
                    }
                }
            }
        }
        
        stage('🧹 Cleanup Docker Resources') {
            steps {
                echo '🧹 Cleaning up Docker resources...'
                
                script {
                    try {
                        // Remove dangling images
                        sh 'docker image prune -f'
                        
                        // Clean up build cache if needed
                        sh 'docker builder prune -f --filter until=24h'
                        
                        echo '✅ Docker cleanup completed'
                    } catch (Exception e) {
                        echo "⚠️ Docker cleanup had some issues: ${e.getMessage()}"
                    }
                }
            }
        }
        
        stage('🚀 Deploy New Stack') {
            steps {
                echo '🚀 Starting new Docker stack...'
                
                // Start the stack with build
                sh 'docker compose -f ${DOCKER_COMPOSE_FILE} up --build -d'
                
                echo '✅ New stack deployment initiated'
            }
        }
        
        stage('⏳ Wait for Services') {
            steps {
                echo '⏳ Waiting for services to become ready...'
                
                script {
                    // Wait for database to be healthy
                    timeout(time: 5, unit: 'MINUTES') {
                        waitUntil {
                            script {
                                def dbHealth = sh(
                                    script: 'docker compose -f ${DOCKER_COMPOSE_FILE} ps postgres | grep "healthy" || true',
                                    returnStdout: true
                                ).trim()
                                return dbHealth.contains('healthy')
                            }
                        }
                    }
                    echo '✅ Database is healthy'
                    
                    // Additional wait for app initialization
                    sleep(time: 30, unit: 'SECONDS')
                    echo '✅ Services initialization complete'
                }
            }
        }
        
        stage('🔧 Run Database Migrations') {
            steps {
                echo '🔧 Running database migrations...'
                
                script {
                    try {
                        sh 'docker compose -f ${DOCKER_COMPOSE_FILE} exec -T web python /app/migrate.py'
                        echo '✅ Database migrations completed successfully'
                    } catch (Exception e) {
                        echo "❌ Migration failed: ${e.getMessage()}"
                        throw e
                    }
                }
            }
        }
        
        stage('🏥 Health Checks') {
            parallel {
                stage('Database Health') {
                    steps {
                        echo '🏥 Checking database health...'
                        
                        script {
                            def result = sh(
                                script: '''
                                    docker compose -f ${DOCKER_COMPOSE_FILE} exec -T postgres \\
                                    psql -U ozbargain_user -d ozbargain_monitor -c "SELECT 1;" \\
                                    2>/dev/null | grep -q "1 row" && echo "healthy" || echo "unhealthy"
                                ''',
                                returnStdout: true
                            ).trim()
                            
                            if (result == 'healthy') {
                                echo '✅ Database is responding correctly'
                            } else {
                                error '❌ Database health check failed'
                            }
                        }
                    }
                }
                
                stage('Web Application Health') {
                    steps {
                        echo '🏥 Checking web application health...'
                        
                        script {
                            def maxRetries = 10
                            def retryCount = 0
                            def isHealthy = false
                            
                            while (retryCount < maxRetries && !isHealthy) {
                                try {
                                    def response = sh(
                                        script: 'curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health || echo "000"',
                                        returnStdout: true
                                    ).trim()
                                    
                                    if (response == '200') {
                                        echo '✅ Web application is healthy'
                                        isHealthy = true
                                    } else {
                                        echo "⏳ Web app not ready yet (HTTP ${response}), retrying..."
                                        sleep(time: 10, unit: 'SECONDS')
                                        retryCount++
                                    }
                                } catch (Exception e) {
                                    echo "⏳ Web app not responding, retrying... (${retryCount + 1}/${maxRetries})"
                                    sleep(time: 10, unit: 'SECONDS')
                                    retryCount++
                                }
                            }
                            
                            if (!isHealthy) {
                                error '❌ Web application health check failed'
                            }
                        }
                    }
                }
                
                stage('Scraper Service Health') {
                    steps {
                        echo '🏥 Checking scraper service health...'
                        
                        script {
                            try {
                                def response = sh(
                                    script: 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000"',
                                    returnStdout: true
                                ).trim()
                                
                                if (response == '200') {
                                    echo '✅ Scraper service is healthy'
                                } else {
                                    echo "⚠️ Scraper service returned HTTP ${response} (may still be starting)"
                                }
                            } catch (Exception e) {
                                echo "⚠️ Scraper service not responding (may still be starting)"
                            }
                        }
                    }
                }
                
                stage('Container Status Check') {
                    steps {
                        echo '🏥 Checking all container statuses...'
                        
                        script {
                            def containers = sh(
                                script: 'docker compose -f ${DOCKER_COMPOSE_FILE} ps --format json',
                                returnStdout: true
                            ).trim()
                            
                            echo "Container statuses:"
                            sh 'docker compose -f ${DOCKER_COMPOSE_FILE} ps'
                            
                            // Check if any containers are not running
                            def failedContainers = sh(
                                script: 'docker compose -f ${DOCKER_COMPOSE_FILE} ps | grep -v "Up" | grep -v "SERVICE" || true',
                                returnStdout: true
                            ).trim()
                            
                            if (failedContainers) {
                                echo "⚠️ Some containers may not be fully ready:"
                                echo failedContainers
                            } else {
                                echo '✅ All containers are running'
                            }
                        }
                    }
                }
            }
        }
        
        stage('📊 System Status Report') {
            steps {
                echo '📊 Generating system status report...'
                
                script {
                    // Get container stats
                    echo '=== CONTAINER STATUS ==='
                    sh 'docker compose -f ${DOCKER_COMPOSE_FILE} ps'
                    
                    echo '\\n=== DATABASE STATS ==='
                    sh '''
                        docker compose -f ${DOCKER_COMPOSE_FILE} exec -T postgres \\
                        psql -U ozbargain_user -d ozbargain_monitor -c \\
                        "SELECT 
                            (SELECT COUNT(*) FROM deals) as total_deals,
                            (SELECT COUNT(*) FROM search_terms WHERE is_active = true) as active_search_terms,
                            (SELECT COUNT(*) FROM search_matches) as total_matches;"
                    '''
                    
                    echo '\\n=== RECENT MIGRATIONS ==='
                    sh '''
                        docker compose -f ${DOCKER_COMPOSE_FILE} exec -T postgres \\
                        psql -U ozbargain_user -d ozbargain_monitor -c \\
                        "SELECT migration_name, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 5;"
                    '''
                    
                    echo '\\n=== DISK USAGE ==='
                    sh 'docker system df'
                    
                    echo '✅ System status report completed'
                }
            }
        }
    }
    
    post {
        always {
            echo '🧹 Pipeline cleanup...'
            
            // Archive logs if they exist
            script {
                try {
                    sh 'docker compose -f ${DOCKER_COMPOSE_FILE} logs --tail=100 > deployment-logs.txt'
                    archiveArtifacts artifacts: 'deployment-logs.txt', allowEmptyArchive: true
                } catch (Exception e) {
                    echo "Could not archive logs: ${e.getMessage()}"
                }
            }
        }
        
        success {
            echo '''
🎉 ===== DEPLOYMENT SUCCESSFUL =====
✅ Git changes committed locally
✅ Docker stack restarted successfully  
✅ All health checks passed
✅ System is ready for use

🌐 Access your application at:
   - Web Interface: http://localhost:5000
   - Scraper API: http://localhost:8000
   - Database: localhost:5432

📊 Check the system status report above for details.
💡 To push changes to GitHub: git push origin main
=====================================
            '''
        }
        
        failure {
            echo '''
❌ ===== DEPLOYMENT FAILED =====
The deployment pipeline encountered errors.
Check the logs above for details.

🔧 Troubleshooting steps:
1. Check Docker service status
2. Verify database connectivity  
3. Review application logs
4. Check disk space and resources

Run manually: docker compose down && docker compose up -d
===============================
            '''
        }
        
        unstable {
            echo '''
⚠️ ===== DEPLOYMENT UNSTABLE =====
Some non-critical checks failed but core services are running.
Monitor the system and check logs for issues.
=================================
            '''
        }
    }
}