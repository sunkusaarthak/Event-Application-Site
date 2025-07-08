import sys
import logging
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from db_manager import DBManager
from dotenv import load_dotenv
from datetime import datetime

# Load .env locally for development
load_dotenv()

# Logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,  # Set to DEBUG for more detail
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("EventApp")

# Validate and log environment variables
required_env = ['SECRT_KEY', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB', 'POOL_SIZE']
missing_env = [var for var in required_env if not os.getenv(var)]
if missing_env:
    logger.error(f"Missing required environment variables: {missing_env}")
    sys.exit(1)
else:
    logger.info("All required environment variables are set.")

try:
    pool_size = int(os.getenv('POOL_SIZE'))
except Exception as e:
    logger.error(f"Invalid POOL_SIZE environment variable: {e}")
    sys.exit(1)

if pool_size < 5:
    logger.warning("POOL_SIZE is less than 5. This may not be sufficient for production workloads.")

db_config = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DB'),
    'ssl_disabled': False
}
logger.info(f"Database config: host={db_config['host']}, db={db_config['database']}, user={db_config['user']}, pool_size={pool_size}")

# Init DBManager with pooling
db = DBManager(db_config, pool_size=pool_size)

app = Flask(__name__)
app.secret_key = os.getenv('SECRT_KEY')

@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr} UA={request.headers.get('User-Agent')}")

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(f"Unhandled Exception: {e}")
    return render_template("error.html", error=str(e)), 500

@app.route('/heartbeat')
def heartbeat():
    logger.debug("Health check /heartbeat called")
    return jsonify({"message": "✌️", "status": "ok"})

@app.route('/', methods=['GET', 'POST'])
def register():
    lang = request.args.get('lang', 'te')
    logger.debug(f"Handling {request.method} request at / from {request.remote_addr} with lang={lang}")
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        street = request.form['street']
        village = request.form['village']
        district = request.form['district']
        pincode = request.form['pincode']
        knowledge_place = request.form.get('knowledge_place', '').strip() or None
        knowledge_date = request.form.get('knowledge_date', '').strip() or None
        logger.info(f"Received registration form from {request.remote_addr} - Name: {name}, Phone: {phone}")

        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            logger.debug("Obtained DB connection from pool")
            cursor = conn.cursor()
            logger.debug("DB cursor created")

            cursor.execute("SELECT id FROM registrations WHERE phone_number = %s", (phone,))
            logger.debug(f"Executed duplicate check for phone: {phone}")
            skip_insert = False
            if cursor.fetchone():
                logger.warning(f"Duplicate registration attempt for phone: {phone} from {request.remote_addr}")
                skip_insert = True

            if not skip_insert:
                insert_sql = """
                    INSERT INTO registrations (name, phone_number, street, village, district, pincode, knowledge_place, knowledge_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (name, phone, street, village, district, pincode, knowledge_place, knowledge_date)
                cursor.execute(insert_sql, values)
                logger.info(f"Inserted registration for phone: {phone}")
                conn.commit()
                logger.debug("DB commit successful")

            cursor.execute("""
                SELECT id FROM registrations
                WHERE phone_number=%s
            """, [phone])
            logger.debug("Fetched registration ID after insert")
            row = cursor.fetchone()

            if row:
                logger.info(f"User ID fetched: {row[0]} for phone: {phone}")
                session['recent_user_id'] = row[0]
                if skip_insert:
                    session['old'] = True
                else:
                    session['old'] = False
                return redirect(url_for('confirmation', lang=lang))
            else:
                logger.warning("Registration inserted but ID not fetched")
                flash("Registered, but could not fetch your ID.", "warning")
                return redirect(url_for('register', lang=lang))

        except Exception as e:
            logger.exception(f"Database error during registration for phone: {phone}")
            flash(f"Database error: {str(e)}", "danger")
            return redirect(url_for('register', lang=lang))
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    logger.debug("Rendering registration form")
    return render_template('form.html', lang=lang, now=datetime.now())

@app.route('/confirmation')
def confirmation():
    lang = request.args.get('lang', 'te')
    user_id = session.get('recent_user_id')
    old_registration = session.get('old')
    logger.info(f"Confirmation page accessed for user_id: {user_id} from {request.remote_addr}")
    if session.get('recent_user_id') is None:
        logger.warning(f"Unauthorized confirmation access attempt for user_id: {user_id}")
        flash("Unauthorized access to confirmation page!", "danger")
        return redirect(url_for('register', lang=lang))

    # Allow access and clear session
    session.pop('recent_user_id', None)
    session.pop('old', None)
    return render_template('confirmation.html', user_id=user_id, old_registration=old_registration, lang=lang)

@app.route('/test-db')
def test_db():
    logger.debug(f"Handling /test-db request from {request.remote_addr}")
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        logger.debug("Obtained DB connection from pool for test-db")
        cursor = conn.cursor()
        cursor.execute("SELECT NOW()")
        now = cursor.fetchone()
        logger.info(f"DB time fetched: {now[0]}")
        return f"DB time is {now[0]}"
    except Exception as e:
        logger.exception("Error during /test-db")
        return f"Error: {e}", 500
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception as close_err:
                logger.error(f"Error closing cursor: {close_err}")
        if conn:
            try:
                conn.close()
            except Exception as close_err:
                logger.error(f"Error closing connection: {close_err}")

@app.route('/admin/fetch/details')
def fetch_details():
    lang = request.args.get('lang', 'en')
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        logger.debug("Obtained DB connection from pool for fetch_details")
        cursor = conn.cursor(dictionary=True)  # dictionary=True returns column names

        cursor.execute("SELECT id, name, phone_number, village, knowledge_date, knowledge_place FROM registrations ORDER BY id ASC")
        logger.debug("Executed Fetch all Query")
        rows = cursor.fetchall()

        for a in rows:
            a['id'] = "RVKKDP" + str(a['id'])

        return render_template('admin.html', registrations=rows, lang=lang)

    except Exception as e:
        logger.exception("Database error during admin fetch")
        flash(f"Database error: {str(e)}", "danger")
        return redirect(url_for('register', lang=lang))
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

@app.route('/admin/export/csv')
def export_csv():
    conn = None
    cursor = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM registrations ORDER BY id ASC")
        rows = cursor.fetchall()

        for a in rows:
            a['id'] = "RVKKDP" + str(a['id'])
        
        # Generate CSV response
        from io import StringIO
        import csv
        from flask import Response

        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(["ID", "Full Name", "Phone", "Village", "District", "Pincode", "Knowledge Date", "Knowledge Place"])  # CSV headers
        # Write row data
        for row in rows:
            writer.writerow([
                row['id'],
                row['name'],
                row['phone_number'],
                row['village'],
                row['district'],
                row['pincode'],
                row['knowledge_date'],
                row['knowledge_place']
            ])

        output = si.getvalue()
        si.close()

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=registrations.csv"}
        )

    except Exception as e:
        flash(f"CSV export failed: {str(e)}", "danger")
        return redirect(url_for('fetch_details'))
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

if __name__ == '__main__':
    try:
        logger.info("Starting Flask app")
        app.run(debug=True)
    except Exception as e:
        logger.exception(f"Flask failed to start: {e}")
        sys.exit(1)