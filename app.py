import sys
import logging
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from db_manager import DBManager
from dotenv import load_dotenv

# Load .env locally for development
load_dotenv()

# Logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,  # Set to DEBUG for more detail
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("EventApp")

app = Flask(__name__)
app.secret_key = os.getenv('SECRT_KEY')

db_config = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DB'),
    'ssl_disabled': False
}

# Init DBManager with pooling
db = DBManager(db_config, pool_size=5)

@app.route('/', methods=['GET', 'POST'])
def register():
    logger.debug(f"Handling {request.method} request at / from {request.remote_addr}")
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        street = request.form['street']
        village = request.form['village']
        district = request.form['district']
        pincode = request.form['pincode']
        logger.info(f"Received registration form from {request.remote_addr} - Name: {name}, Phone: {phone}")

        try:
            conn = db.get_connection()
            logger.debug("Obtained DB connection from pool")
            cursor = conn.cursor()
            logger.debug("DB cursor created")

            cursor.execute("SELECT id FROM registrations WHERE phone_number = %s", (phone,))
            logger.debug(f"Executed duplicate check for phone: {phone}")
            if cursor.fetchone():
                logger.warning(f"Duplicate registration attempt for phone: {phone} from {request.remote_addr}")
                flash("Phone number already registered!", "danger")
                cursor.close()
                conn.close()
                logger.debug("Closed DB cursor and connection after duplicate")
                return redirect(url_for('register'))

            insert_sql = """
                INSERT INTO registrations (name, phone_number, street, village, district, pincode)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (name, phone, street, village, district, pincode)
            cursor.execute(insert_sql, values)
            logger.info(f"Inserted registration for phone: {phone}")
            conn.commit()
            logger.debug("DB commit successful")

            cursor.execute("""
                SELECT id FROM registrations
                WHERE name=%s AND phone_number=%s AND street=%s AND village=%s AND district=%s AND pincode=%s
                ORDER BY id DESC LIMIT 1
            """, values)
            logger.debug("Fetched registration ID after insert")
            row = cursor.fetchone()

            cursor.close()
            conn.close()
            logger.debug("Closed DB cursor and connection after registration")

            if row:
                logger.info(f"User ID fetched: {row[0]} for phone: {phone}")
                return redirect(url_for('confirmation', user_id=row[0]))
            else:
                logger.warning("Registration inserted but ID not fetched")
                flash("Registered, but could not fetch your ID.", "warning")
                return redirect(url_for('register'))

        except Exception as e:
            logger.exception(f"Database error during registration for phone: {phone}")
            flash(f"Database error: {str(e)}", "danger")
            return redirect(url_for('register'))

    logger.debug("Rendering registration form")
    return render_template('form.html')

@app.route('/confirmation/<int:user_id>')
def confirmation(user_id):
    logger.info(f"Confirmation page accessed for user_id: {user_id} from {request.remote_addr}")
    return render_template('confirmation.html', user_id=user_id)

@app.route('/test-db')
def test_db():
    logger.debug(f"Handling /test-db request from {request.remote_addr}")
    try:
        conn = db.get_connection()
        logger.debug("Obtained DB connection from pool for test-db")
        cursor = conn.cursor()
        cursor.execute("SELECT NOW()")
        now = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.debug("Closed DB cursor and connection for test-db")
        return f"DB time is {now[0]}"
    except Exception as e:
        logger.exception("Error during /test-db")
        return f"Error: {e}", 500

if __name__ == '__main__':
    logger.info("Starting Flask app")
    app.run(debug=True)