#!/usr/bin/env python3
"""
Production logging and monitoring configuration.
Enhanced version with comprehensive logging, metrics, and health checks.
"""

import os
import logging
import logging.handlers
from datetime import datetime
import json
from flask import request, g
import time

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

def setup_logging(app):
    """Set up comprehensive logging for the Flask application."""
    
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(level=getattr(logging, log_level))
    
    # Create formatters
    json_formatter = JSONFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=10  # 10MB per file, keep 10 files
    )
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure Flask app logger
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(getattr(logging, log_level))
    
    # Configure other loggers
    for logger_name in ['sqlalchemy', 'requests', 'urllib3']:
        logger = logging.getLogger(logger_name)
        logger.addHandler(file_handler)
        logger.setLevel(logging.WARNING)
    
    # Add request logging middleware
    @app.before_request
    def log_request_info():
        g.start_time = time.time()
        app.logger.info('Request started', extra={
            'method': request.method,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'request_id': id(request)
        })
    
    @app.after_request
    def log_request_result(response):
        duration = time.time() - g.get('start_time', time.time())
        app.logger.info('Request completed', extra={
            'method': request.method,
            'url': request.url,
            'status_code': response.status_code,
            'duration_seconds': round(duration, 3),
            'content_length': response.content_length,
            'request_id': id(request)
        })
        return response
    
    return app.logger

def setup_performance_monitoring(app):
    """Set up performance monitoring and metrics collection."""
    
    # Metrics storage (in production, use Redis or a metrics service)
    metrics = {
        'requests_total': 0,
        'requests_by_status': {},
        'request_duration_sum': 0,
        'database_queries': 0,
        'ai_summarizations': 0,
        'alerts_sent': 0
    }
    
    @app.before_request
    def track_request_metrics():
        g.start_time = time.time()
        metrics['requests_total'] += 1
    
    @app.after_request
    def track_response_metrics(response):
        # Track response time
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            metrics['request_duration_sum'] += duration
        
        # Track status codes
        status = str(response.status_code)
        metrics['requests_by_status'][status] = metrics['requests_by_status'].get(status, 0) + 1
        
        return response
    
    # Metrics endpoint
    @app.route('/metrics')
    def metrics_endpoint():
        """Prometheus-compatible metrics endpoint."""
        avg_duration = (metrics['request_duration_sum'] / metrics['requests_total'] 
                       if metrics['requests_total'] > 0 else 0)
        
        prometheus_metrics = f"""# HELP competitive_intel_requests_total Total number of requests
# TYPE competitive_intel_requests_total counter
competitive_intel_requests_total {metrics['requests_total']}

# HELP competitive_intel_request_duration_average Average request duration
# TYPE competitive_intel_request_duration_average gauge
competitive_intel_request_duration_average {avg_duration}

# HELP competitive_intel_database_queries_total Total database queries
# TYPE competitive_intel_database_queries_total counter
competitive_intel_database_queries_total {metrics['database_queries']}

# HELP competitive_intel_ai_summarizations_total Total AI summarizations
# TYPE competitive_intel_ai_summarizations_total counter
competitive_intel_ai_summarizations_total {metrics['ai_summarizations']}

# HELP competitive_intel_alerts_sent_total Total alerts sent
# TYPE competitive_intel_alerts_sent_total counter
competitive_intel_alerts_sent_total {metrics['alerts_sent']}
"""
        
        for status, count in metrics['requests_by_status'].items():
            prometheus_metrics += f'competitive_intel_requests_by_status{{status="{status}"}} {count}\n'
        
        return prometheus_metrics, 200, {'Content-Type': 'text/plain'}
    
    return metrics

class DatabaseMonitor:
    """Monitor database performance and health."""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def check_connection_pool(self):
        """Check database connection pool status."""
        try:
            pool = self.db.engine.pool
            return {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalidated()
            }
        except Exception as e:
            self.logger.error(f"Failed to get connection pool stats: {e}")
            return None
