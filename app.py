from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Try to import Google Secret Manager (for GCP deployment)
try:
    from google.cloud import secretmanager
    USE_SECRET_MANAGER = True
except ImportError:
    USE_SECRET_MANAGER = False

app = Flask(__name__, static_folder='images', template_folder='.')

def get_secret(secret_id):
    """Get secret from Google Secret Manager or environment variable"""
    if USE_SECRET_MANAGER and os.environ.get('GOOGLE_CLOUD_PROJECT'):
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            print(f"Error fetching secret {secret_id}: {e}")
    
    # Fallback to environment variable
    return os.environ.get(secret_id)

# File to store visitor statistics
STATS_FILE = 'visitor_stats.json'

def load_stats():
    """Load visitor statistics from file"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {
        'total_hits': 0,
        'weekly_hits': 0,
        'page_hits': {},
        'last_reset': datetime.now().isoformat(),
        'history': []
    }

def save_stats(stats):
    """Save visitor statistics to file"""
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def record_hit(page):
    """Record a page hit"""
    stats = load_stats()
    stats['total_hits'] += 1
    stats['weekly_hits'] += 1
    
    if page not in stats['page_hits']:
        stats['page_hits'][page] = 0
    stats['page_hits'][page] += 1
    
    save_stats(stats)

def send_weekly_report():
    """Send weekly visitor statistics via email"""
    try:
        stats = load_stats()
        
        # Email configuration
        sender_email = get_secret('SENDER_EMAIL')
        sender_password = get_secret('SENDER_PASSWORD')
        recipient_email = 'mikkilimanohar@gmail.com'
        
        if not sender_email or not sender_password:
            print("Email credentials not configured")
            return
        
        # Prepare the report
        last_reset = datetime.fromisoformat(stats['last_reset'])
        current_date = datetime.now()
        
        page_breakdown = "\n".join([f"  - {page}: {count} visits" 
                                    for page, count in stats['page_hits'].items()])
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Weekly Website Statistics - {current_date.strftime('%B %d, %Y')}"
        
        body = f"""
Hello,

Here is your weekly website statistics report:

📊 WEEKLY SUMMARY
Period: {last_reset.strftime('%B %d, %Y')} - {current_date.strftime('%B %d, %Y')}
Total Visits This Week: {stats['weekly_hits']}
Total All-Time Visits: {stats['total_hits']}

📄 PAGE BREAKDOWN
{page_breakdown if page_breakdown else "  No page data available"}

---
This is an automated weekly report from your CV website.
To stop receiving these reports, please contact your administrator.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(f"Weekly report sent successfully at {current_date}")
        
        # Archive the week's stats and reset weekly counter
        stats['history'].append({
            'week_ending': current_date.isoformat(),
            'weekly_hits': stats['weekly_hits'],
            'page_hits': stats['page_hits'].copy()
        })
        stats['weekly_hits'] = 0
        stats['page_hits'] = {}
        stats['last_reset'] = current_date.isoformat()
        save_stats(stats)
        
    except Exception as e:
        print(f"Error sending weekly report: {str(e)}")

# Set up scheduler for weekly reports (every Monday at 9 AM)
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=send_weekly_report, 
    trigger="cron", 
    day_of_week='mon', 
    hour=9, 
    minute=0,
    id='weekly_report',
    name='Weekly Statistics Report'
)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.before_request
def track_visitor():
    """Track visitor for each request"""
    # Only track HTML page requests, not static files
    if request.path.startswith('/images/') or request.path.startswith('/static/'):
        return
    record_hit(request.path)

# Serve index.html at root
@app.route('/')
def index():
    return render_template('index.html')

# Serve contact.html
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Serve projects root -> redirect to work projects
@app.route('/projects')
def projects():
    return redirect(url_for('projects_work'))

# Serve work projects page
@app.route('/projects/work')
def projects_work():
    return render_template('projects.html')

# Serve outside-work projects page
@app.route('/projects/outside')
def projects_outside():
    return render_template('outside-work.html')

# Handle contact form submission
@app.route('/send-message', methods=['POST'])
def send_message():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Email configuration
        sender_email = get_secret('SENDER_EMAIL')
        sender_password = get_secret('SENDER_PASSWORD')
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

# Admin route to view statistics (optional)
@app.route('/admin/stats')
def view_stats():
    """View current visitor statistics"""
    stats = load_stats()
    return jsonify(stats)

# Admin route to manually trigger weekly report
@app.route('/admin/send-report')
def manual_report():
    """Manually trigger the weekly report email"""
    try:
        send_weekly_report()
        return jsonify({
            'success': True,
            'message': 'Weekly report sent successfully to mikkilimanohar@gmail.com'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error sending report: {str(e)}'
        }), 500

# Admin route to update report schedule
@app.route('/admin/schedule', methods=['GET', 'POST'])
def manage_schedule():
    """View or update the weekly report schedule"""
    if request.method == 'GET':
        # Get current schedule from scheduler
        jobs = scheduler.get_jobs()
        schedule_info = []
        for job in jobs:
            schedule_info.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jsonify({'schedules': schedule_info})
    
    elif request.method == 'POST':
        # Update schedule
        try:
            data = request.get_json()
            day = data.get('day_of_week', 'mon')  # mon, tue, wed, thu, fri, sat, sun
            hour = int(data.get('hour', 9))  # 0-23
            minute = int(data.get('minute', 0))  # 0-59
            
            # Remove old job and add new one
            scheduler.remove_job('weekly_report')
            scheduler.add_job(
                func=send_weekly_report,
                trigger="cron",
                day_of_week=day,
                hour=hour,
                minute=minute,
                id='weekly_report',
                name='Weekly Statistics Report'
            )
            
            return jsonify({
                'success': True,
                'message': f'Schedule updated to every {day.upper()} at {hour:02d}:{minute:02d}'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error updating schedule: {str(e)}'
            }), 500

# Admin dashboard HTML
@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for managing visitor tracking"""
    stats = load_stats()
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - Visitor Statistics</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .card {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }}
            .stat {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
            button {{ background: #4CAF50; color: white; padding: 10px 20px; border: none; 
                     border-radius: 4px; cursor: pointer; font-size: 16px; margin: 5px; }}
            button:hover {{ background: #45a049; }}
            .danger {{ background: #f44336; }}
            .danger:hover {{ background: #da190b; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #2196F3; color: white; }}
            input {{ padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <h1>📊 Admin Dashboard</h1>
        
        <div class="card">
            <h2>Current Statistics</h2>
            <p>Total All-Time Visits: <span class="stat">{stats['total_hits']}</span></p>
            <p>This Week's Visits: <span class="stat">{stats['weekly_hits']}</span></p>
            <p>Last Reset: {stats['last_reset']}</p>
            
            <h3>Page Breakdown</h3>
            <table>
                <tr><th>Page</th><th>Visits</th></tr>
                {''.join([f"<tr><td>{page}</td><td>{count}</td></tr>" for page, count in stats['page_hits'].items()])}
            </table>
        </div>
        
        <div class="card">
            <h2>Weekly Report Management</h2>
            <button onclick="sendReport()">📧 Send Report Now</button>
            <button onclick="viewSchedule()">📅 View Schedule</button>
            <p id="result"></p>
            
            <h3>Update Schedule</h3>
            <form onsubmit="updateSchedule(event)">
                <label>Day of Week:</label>
                <select id="day" name="day">
                    <option value="mon">Monday</option>
                    <option value="tue">Tuesday</option>
                    <option value="wed">Wednesday</option>
                    <option value="thu">Thursday</option>
                    <option value="fri">Friday</option>
                    <option value="sat">Saturday</option>
                    <option value="sun">Sunday</option>
                </select>
                
                <label>Hour (0-23):</label>
                <input type="number" id="hour" name="hour" min="0" max="23" value="9">
                
                <label>Minute (0-59):</label>
                <input type="number" id="minute" name="minute" min="0" max="59" value="0">
                
                <button type="submit">Update Schedule</button>
            </form>
        </div>
        
        <script>
            function sendReport() {{
                document.getElementById('result').innerHTML = 'Sending report...';
                fetch('/admin/send-report')
                    .then(res => res.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            `<strong>${{data.success ? '✅' : '❌'}}</strong> ${{data.message}}`;
                    }})
                    .catch(err => {{
                        document.getElementById('result').innerHTML = '❌ Error: ' + err;
                    }});
            }}
            
            function viewSchedule() {{
                fetch('/admin/schedule')
                    .then(res => res.json())
                    .then(data => {{
                        const schedules = data.schedules.map(s => 
                            `Job: ${{s.name || s.id}}<br>Trigger: ${{s.trigger}}<br>Next Run: ${{s.next_run || 'N/A'}}`
                        ).join('<br><br>');
                        document.getElementById('result').innerHTML = schedules;
                    }});
            }}
            
            function updateSchedule(event) {{
                event.preventDefault();
                const day = document.getElementById('day').value;
                const hour = document.getElementById('hour').value;
                const minute = document.getElementById('minute').value;
                
                fetch('/admin/schedule', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{day_of_week: day, hour: hour, minute: minute}})
                }})
                .then(res => res.json())
                .then(data => {{
                    document.getElementById('result').innerHTML = 
                        `<strong>${{data.success ? '✅' : '❌'}}</strong> ${{data.message}}`;
                }});
            }}
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
