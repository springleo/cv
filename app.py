from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__, static_folder='images', template_folder='.')

# Serve index.html at root
@app.route('/')
def index():
    return render_template('index.html')

# Serve contact.html
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Serve static images
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
