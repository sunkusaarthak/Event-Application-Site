from flask import Flask, render_template, request, redirect, url_for, flash
from db_manager import DBManager

app = Flask(__name__)
app.secret_key = ''

# MySQL config
db_config = {
    'host': 'mysql',
    'port': '',  # Replace with your actual port
    'user': '',
    'password': '',
    'database': '',
    'ssl_disabled': False
}

# Init DBManager with pooling
db = DBManager(db_config, pool_size=5)

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        street = request.form['street']
        village = request.form['village']
        district = request.form['district']
        pincode = request.form['pincode']

        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM registrations WHERE phone_number = %s", (phone,))
            if cursor.fetchone():
                flash("Phone number already registered!", "danger")
                cursor.close()
                conn.close()
                return redirect(url_for('register'))

            insert_sql = """
                INSERT INTO registrations (name, phone_number, street, village, district, pincode)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (name, phone, street, village, district, pincode)
            cursor.execute(insert_sql, values)
            conn.commit()

            cursor.execute("""
                SELECT id FROM registrations
                WHERE name=%s AND phone_number=%s AND street=%s AND village=%s AND district=%s AND pincode=%s
                ORDER BY id DESC LIMIT 1
            """, values)
            row = cursor.fetchone()

            cursor.close()
            conn.close()

            if row:
                return redirect(url_for('confirmation', user_id=row[0]))
            else:
                flash("Registered, but could not fetch your ID.", "warning")
                return redirect(url_for('register'))

        except Exception as e:
            flash(f"Database error: {str(e)}", "danger")
            return redirect(url_for('register'))

    return render_template('form.html')

@app.route('/confirmation/<int:user_id>')
def confirmation(user_id):
    return render_template('confirmation.html', user_id=user_id)

@app.route('/test-db')
def test_db():
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT NOW()")
        now = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"DB time is {now[0]}"
    except Exception as e:
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)