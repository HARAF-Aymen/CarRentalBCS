from app import create_app
import os
from flask import send_from_directory

app = create_app()
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'uploads'), filename)
