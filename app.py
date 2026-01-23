from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_folder='images', template_folder='.')

# Serve index.html at root
@app.route('/')
def index():
    return render_template('index.html')

# Serve contact.html
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Serve projects page
@app.route('/projects')
def projects():
    return render_template('projects.html')

# Handle contact form submission
@app.route('/send-message', methods=['POST'])
def send_message():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Email configuration - these should come from environment variables (GitHub Secrets)
        sender_email = os.environ.get('SENDER_EMAIL')
        sender_password = os.environ.get('SENDER_PASSWORD')
        recipient_email = 'mikkilimanohar@gmail.com'
        
        # Validate that credentials are set
        if not sender_email or not sender_password:
            return render_template('contact.html', success=False, message="Email service is not configured. Please try again later.")
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"New Contact Form Submission from {name}"
        
        body = f"""
Hello,

You have received a new message from your contact form:

Name: {name}
Email: {email}

Message:
{message}

---
This is an automated message from your CV website.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return render_template('contact.html', success=True, message="Message sent successfully! Check your inbox.")
    except Exception as e:
        return render_template('contact.html', success=False, message=f"Error sending message: {str(e)}")

# Serve static images
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
