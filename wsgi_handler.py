# wsgi_handler.py
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

try:
    import serverless_wsgi
    from app import app
    
    def handler(event, context):
        return serverless_wsgi.handle_request(app, event, context)
        
except ImportError as e:
    print(f"Import error: {e}")
    
    def handler(event, context):
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"error": "Failed to import required modules"}'
        }
