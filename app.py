from flask import Flask, render_template, request, redirect, url_for, jsonify, abort, session, make_response, send_file
import json
import os
import uuid
from datetime import datetime, timedelta
import csv
from io import StringIO
from user_agents import parse
from flask_mail import Mail, Message
from io import BytesIO
import qrcode
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64




from bs4 import BeautifulSoup
import requests

def fetch_url_metadata(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.title.string if soup.title else "No Title"
        description = soup.find("meta", attrs={"name": "description"})
        description = description["content"] if description else "No Description"
        thumbnail = soup.find("meta", attrs={"property": "og:image"})
        thumbnail = thumbnail["content"] if thumbnail else None

        return {
            "title": title,
            "description": description,
            "thumbnail": thumbnail
        }
    except Exception as e:
        return {
            "title": "No Title",
            "description": "No Description",
            "thumbnail": None
        }
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for session management


# dusted
# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-email-password'  # Replace with your email password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'  # Replace with your email

mail = Mail(app)

# File paths
USERS_FILE = "data/users.json"
URLS_FILE = "data/urls.json"
ANALYTICS_FILE = "data/analytics.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Load JSON data
def load_json(file):
    if not os.path.exists(file):
        return {}  # Return an empty dictionary if the file doesn't exist
    try:
        with open(file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}  # Return an empty dictionary if the file contains invalid JSON

# Save JSON data
def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# Generate a short URL
def generate_short_url():
    return str(uuid.uuid4())[:8]

# Extract domain name from URL
def extract_domain(url):
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc or "Unknown Domain"


# Home page (redirect to login if not authenticated)
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")



def send_expiration_notification(username, email, short_url, original_url, expires_at):
    subject = "Link Expiration Notification"
    body = f"""
    Hello {username},

    Your shortened URL is about to expire.

    Short URL: {short_url}
    Original URL: {original_url}
    Expiration Date: {expires_at}

    Please take necessary action.

    Regards,
    URL Shortener Team
    """
    msg = Message(subject, recipients=[email], body=body)
    mail.send(msg)


# Check for expiring links and send notifications
def check_expiring_links():
    urls = load_json(URLS_FILE)
    users = load_json(USERS_FILE)

    for short_url, data in urls.items():
        if data["expires_at"]:
            expires_at = datetime.strptime(data["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expires_at - timedelta(days=1):  # Notify 1 day before expiration
                username = data["created_by"]
                user_email = users.get(username, {}).get("email")  # Assuming email is stored in users.json
                if user_email:
                    send_expiration_notification(username, user_email, data["short_url"], data["original_url"], data["expires_at"])




# Bulk URL Shortening
@app.route("/bulk-shorten", methods=["POST"])
def bulk_shorten():
    if "username" not in session:
        return redirect(url_for("login"))

    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    if file and file.filename.endswith(('.csv', '.xlsx', '.ods')):
        urls = load_json(URLS_FILE)
        users = load_json(USERS_FILE)
        username = session["username"]

        # Read the file based on its format
        if file.filename.endswith('.csv'):
            csv_data = file.read().decode("utf-8")
            csv_reader = csv.reader(StringIO(csv_data))
            rows = list(csv_reader)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            rows = df.values.tolist()
        elif file.filename.endswith('.ods'):
            df = pd.read_excel(file, engine='odf')
            rows = df.values.tolist()

        shortened_urls = []

        for i, row in enumerate(rows):
            original_url = row[0]
            if not original_url:
                continue

            # Generate a short URL
            short_url = generate_short_url()
            default_name = f"ExcelData{i+1}"
            urls[short_url] = {
                "short_url": f"http://localhost:5000/{short_url}",
                "original_url": original_url,
                "name": default_name,  # Default name
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": None,  # No expiration by default
                "clicks": [],
                "created_by": username
            }
            shortened_urls.append([original_url, f"http://localhost:5000/{short_url}", default_name])

        # Save the updated URLs
        save_json(URLS_FILE, urls)

        # Add the short URLs to the user's history
        users[username]["history"].extend([short_url for _, short_url, _ in shortened_urls])
        save_json(USERS_FILE, users)

        # Create a CSV response for the shortened URLs
        csv_output = StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(["Original URL", "Shortened URL", "Name"])
        csv_writer.writerows(shortened_urls)

        response = make_response(csv_output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=shortened_urls.csv"
        response.headers["Content-type"] = "text/csv"
        return response

    return "Invalid file format. Please upload a CSV, XLSX, or ODS file.", 400


# Update URL name
@app.route("/update-name/<short_url>", methods=["POST"])
def update_name(short_url):
    if "username" not in session:
        return redirect(url_for("login"))

    new_name = request.form.get("name")
    if not new_name:
        return "Name is required", 400

    urls = load_json(URLS_FILE)
    if short_url in urls and urls[short_url]["created_by"] == session["username"]:
        urls[short_url]["name"] = new_name
        save_json(URLS_FILE, urls)
        return redirect(url_for("dashboard"))

    return "URL not found", 404



# @app.route("/<short_url>")
# def redirect_to_original(short_url):
#     urls = load_json(URLS_FILE)
#     if short_url not in urls:
#         abort(404)

#     url_data = urls[short_url]

#     # Check if the URL is password-protected
#     if url_data.get("password"):
#         password = request.args.get("password")
#         if password != url_data["password"]:
#             return render_template("password_prompt.html", short_url=short_url)

#     return redirect(url_data["original_url"])



# Shorten URL (protected route)
@app.route("/shorten", methods=["POST"])
def shorten_url():
    if "username" not in session:
        return redirect(url_for("login"))

    original_url = request.form.get("url")
    custom_short_url = request.form.get("custom_short_url")
    expiration_days = request.form.get("expiration_days")
    password = request.form.get("password")

    if not original_url:
        return "URL is required", 400

    urls = load_json(URLS_FILE)

    # Fetch metadata
    metadata = fetch_url_metadata(original_url)


    # Check if the custom short URL is already taken
    if custom_short_url:
        if custom_short_url in urls:
            return "Custom short URL already exists", 400
        short_url = custom_short_url
    else:
        # Generate a random short URL
        short_url = generate_short_url()

    # Check if the original URL already exists for the user
    for existing_short_url, data in urls.items():
        if data["original_url"] == original_url and data["created_by"] == session["username"]:
            return jsonify({"short_url": data["short_url"]})

    # Calculate expiration date
    expires_at = None
    if expiration_days and expiration_days.isdigit():
        expires_at = (datetime.now() + timedelta(days=int(expiration_days))).strftime("%Y-%m-%d %H:%M:%S")

    # Save URL mapping
    urls[short_url] = {
        "short_url": f"http://localhost:5000/{short_url}",  # Store shortened URL
        "original_url": original_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at,  # Set expiration date (or None if no expiration)
        "clicks": [],
        "created_by": session["username"],  # Track which user created the short URL
        "metadata": metadata,  # Store metadata
        "password": password
    }
    save_json(URLS_FILE, urls)

    # Add the short URL to the user's history
    users = load_json(USERS_FILE)
    users[session["username"]]["history"].append(short_url)
    save_json(USERS_FILE, users)

    return jsonify({"short_url": f"http://localhost:5000/{short_url}"})


# Delete a history entry
@app.route("/delete/<short_url>", methods=["POST"])
def delete_history(short_url):
    if "username" not in session:
        return redirect(url_for("login"))

    urls = load_json(URLS_FILE)
    users = load_json(USERS_FILE)

    if short_url in urls and urls[short_url]["created_by"] == session["username"]:
        # Remove from URLs
        del urls[short_url]
        save_json(URLS_FILE, urls)

        # Remove from user's history
        users[session["username"]]["history"] = [url for url in users[session["username"]]["history"] if url != short_url]
        save_json(USERS_FILE, users)

    return redirect(url_for("dashboard"))

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_json(USERS_FILE)
        if username in users:
            return "Username already exists", 400

        users[username] = {"password": password, "history": []}
        save_json(USERS_FILE, users)

        return redirect(url_for("login"))

    return render_template("signup.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = load_json(USERS_FILE)
        if username not in users or users[username]["password"] != password:
            return "Invalid credentials", 401

        # Set the user's session
        session["username"] = username
        return redirect(url_for("index"))

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# Download history as CSV
@app.route("/download-history")
def download_history():
    if "username" not in session:
        return redirect(url_for("login"))

    users = load_json(USERS_FILE)
    urls = load_json(URLS_FILE)
    username = session["username"]

    # Prepare CSV data
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    csv_writer.writerow(["Short URL", "Original URL", "Created At", "Expires At", "Clicks"])

    for short_url in users[username]["history"]:
        if short_url in urls:
            url_data = urls[short_url]
            clicks = []
            for click in url_data.get("clicks", []):
                # Ensure all required keys are present
                device = click.get("device", "Unknown Device")
                os = click.get("os", "Unknown OS")
                browser = click.get("browser", "Unknown Browser")
                timestamp = click.get("timestamp", "Unknown Time")
                clicks.append(f"Device: {device}, OS: {os}, Browser: {browser}, Time: {timestamp}")

            clicks_str = "\n".join(clicks)
            csv_writer.writerow([
                url_data["short_url"],
                url_data["original_url"],
                url_data["created_at"],
                url_data.get("expires_at", "No expiration"),
                clicks_str
            ])

    # Create a response with the CSV data
    response = make_response(csv_data.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={username}_history.csv"
    response.headers["Content-type"] = "text/csv"
    return response




# 404 Error Handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404



# Generate QR code for a short URL
@app.route("/qr/<short_url>")
def generate_qr(short_url):
    urls = load_json(URLS_FILE)
    if short_url not in urls:
        abort(404)

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(urls[short_url]["short_url"])
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")

    # Save QR code to a BytesIO object
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

# Track geolocation using ipinfo.io (free tier)
def get_geolocation(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        data = response.json()
        return data.get("city", "Unknown"), data.get("region", "Unknown"), data.get("country", "Unknown")
    except:
        return "Unknown", "Unknown", "Unknown"

# Update the redirect_to_original route to track geolocation and referrers
@app.route("/<short_url>")
def redirect_to_original(short_url):
    urls = load_json(URLS_FILE)
    if short_url not in urls:
        abort(404)

    url_data = urls[short_url]

    # Check if the URL is password-protected
    if url_data.get("password"):
        password = request.args.get("password")
        if password != url_data["password"]:
            return render_template("password_prompt.html", short_url=short_url)

    # Check if the URL has expired
    if url_data["expires_at"]:
        expires_at = datetime.strptime(url_data["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expires_at:
            return "This URL has expired.", 410  # 410 Gone status code

    # Parse the user agent string
    user_agent_str = request.headers.get("User-Agent")
    user_agent = parse(user_agent_str)

    # Extract device, OS, and browser information
    device = user_agent.device.family or "Unknown Device"
    os = f"{user_agent.os.family} {user_agent.os.version_string}"
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"

    # Get geolocation data
    ip = request.remote_addr
    city, region, country = get_geolocation(ip)

    # Add click details
    click_data = {
        "device": device,
        "os": os,
        "browser": browser,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "city": city,
        "region": region,
        "country": country,
        "referrer": request.referrer or "Direct"
    }

    # Ensure clicks is a list
    if isinstance(url_data["clicks"], int):
        url_data["clicks"] = []  # Convert to a list if it's an integer
    url_data["clicks"].append(click_data)

    save_json(URLS_FILE, urls)

    return redirect(url_data["original_url"])
# Generate click trends graph
def generate_click_trends(clicks):
    click_dates = [datetime.strptime(click["timestamp"], "%Y-%m-%d %H:%M:%S").date() for click in clicks]
    click_counts = {}
    for date in click_dates:
        click_counts[date] = click_counts.get(date, 0) + 1

    sorted_dates = sorted(click_counts.keys())
    sorted_clicks = [click_counts[date] for date in sorted_dates]

    # Plot click trends
    plt.figure(figsize=(10, 5))
    plt.plot(sorted_dates, sorted_clicks, marker="o")
    plt.xlabel("Date")
    plt.ylabel("Clicks")
    plt.title("Click Trends Over Time")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()  # Close the plot to free up memory

    # Encode the plot as base64
    plot_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return plot_base64

def generate_bar_graph(user_history):
    # Extract data for the bar graph
    urls = [item["short_url"].split("/")[-1] for item in user_history]  # Short URLs
    clicks = [len(item["clicks"]) for item in user_history]  # Number of clicks per URL

    # Create the bar graph
    plt.figure(figsize=(10, 5))
    plt.bar(urls, clicks, color='skyblue')
    plt.xlabel("Short URLs")
    plt.ylabel("Number of Clicks")
    plt.title("Clicks per Shortened URL")
    plt.xticks(rotation=45, ha="right")  # Rotate x-axis labels for better readability
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()  # Close the plot to free up memory

    # Encode the plot as base64
    plot_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return plot_base64


# Update the dashboard route to include the click trends graph
@app.route("/dashboard")
@app.route("/dashboard/<int:page>")
def dashboard(page=1):
    if "username" not in session:
        return redirect(url_for("login"))

    users = load_json(USERS_FILE)
    urls = load_json(URLS_FILE)
    username = session["username"]

    # Get the user's history with full details
    user_history = []
    for short_url in users[username]["history"]:
        if short_url in urls:
            url_data = urls[short_url]
            # Ensure metadata exists
            if "metadata" not in url_data:
                url_data["metadata"] = {
                    "title": "No Title",
                    "description": "No Description",
                    "thumbnail": None
                }
            user_history.append(urls[short_url])

    # Generate click trends graph
    all_clicks = []
    for item in user_history:
        all_clicks.extend(item["clicks"])
    plot_base64 = generate_click_trends(all_clicks)

    # Generate bar graph for clicks per URL
    bar_graph_base64 = generate_bar_graph(user_history)

    # Pagination logic
    per_page = 10
    total = len(user_history)
    start = (page - 1) * per_page
    end = start + per_page

    return render_template(
        "dashboard.html",
        username=username,
        history=user_history,
        start=start,
        end=end,
        total=total,
        page=page,
        plot_base64=plot_base64,
        bar_graph_base64=bar_graph_base64  # Pass the bar graph to the template
    )

'''from apscheduler.schedulers.background import BackgroundScheduler

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_expiring_links, trigger="interval", days=1)  # Run daily
scheduler.start()

# Ensure the scheduler shuts down when the app stops
@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    scheduler.shutdown()'''


if __name__ == "__main__":
    app.run(debug=True)
