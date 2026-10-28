import os
import sys
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

def main():
    print("=" * 65)
    print("  GMAIL SMTP LIVE EMAIL CONFIGURATION SETUP")
    print("=" * 65)
    print("To allow the review system to send emails via Gmail, Google requires")
    print("a 16-character 'App Password'.")
    print()
    print("Steps to get your 16-character App Password (takes 30 seconds):")
    print("  1. Visit: https://myaccount.google.com/apppasswords")
    print("     (Make sure 2-Step Verification is turned on on your Google account)")
    print("  2. App name: Enter 'Automated Review System'")
    print("  3. Click 'Create'")
    print("  4. Copy the generated 16-character code (e.g. 'abcd efgh ijkl mnop')")
    print("-" * 65)
    
    email = input("Enter your Gmail address (e.g. your-email@gmail.com): ").strip()
    if not email or "@" not in email:
        print("Invalid email address. Aborted.")
        return
        
    app_password = input("Enter your 16-character App Password: ").strip().replace(" ", "")
    if not app_password:
        print("Password cannot be empty. Aborted.")
        return

    sender_name = input("Enter Display Sender Name [Nexus Review AI]: ").strip() or "Nexus Review AI"
    
    print("\nVerifying connection to smtp.gmail.com:587...")
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
        server.starttls()
        server.login(email, app_password)
        server.quit()
        print("Authentication SUCCESSFUL! Gmail credentials verified.")
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Please check your email and 16-character App Password and try again.")
        return

    # Save to SQLite database
    db_path = os.path.join(os.path.dirname(__file__), "backend", "system.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_enabled', 'true')")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_host', 'smtp.gmail.com')")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_port', '587')")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_user', ?)", (email,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_password', ?)", (app_password,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_from_email', ?)", (email,))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('smtp_from_name', ?)", (sender_name,))
    conn.commit()
    conn.close()
    
    print("\nCredentials saved to system database!")
    print("All review evaluations and invitation emails will now be automatically sent through this Gmail address!")

    # Ask if user wants to send a test email
    test_target = input(f"\nSend a test email to {email}? [Y/n]: ").strip().lower()
    if test_target in ("", "y", "yes"):
        print(f"Sending test email to {email}...")
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "[Verified] Nexus Review AI Live Gmail Connection"
            msg["From"] = formataddr((sender_name, email))
            msg["To"] = email
            msg.attach(MIMEText("<h2>Gmail SMTP Connected Successfully!</h2><p>Your automated review system is now live and will automatically dispatch emails to students and interns.</p>", "html", "utf-8"))
            
            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
            server.starttls()
            server.login(email, app_password)
            server.sendmail(email, [email], msg.as_string())
            server.quit()
            print(f"Test email sent! Please check your inbox at {email}.")
        except Exception as e:
            print(f"Failed to send test email: {e}")

if __name__ == "__main__":
    main()

