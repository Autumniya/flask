import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_caching import Cache
from vercel_postgres import sql as vercel_sql

app = Flask(__name__)

# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'  # For production, consider 'filesystem' and set CACHE_DIR
cache = Cache(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='image/favicon.ico'), code=302)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    data = request.get_json()
    user_id = data.get('userId')
    order_id = data.get('orderId')
    amount = data.get('amount')
    plan_id = data.get('planId')
    pay_token = data.get('pay_token')
    end_date_str = data.get('end_date')
    enddate = datetime.strptime(end_date_str, '%d-%B-%Y')

    try:
        # Check for existing active subscription
        existing_subscription = vercel_sql.execute("SELECT * FROM subscriptions WHERE user_id = %s AND plan_id = %s AND is_active = TRUE", (user_id, plan_id)).fetchone()
        
        if existing_subscription:
            # Update existing subscription
            vercel_sql.execute("UPDATE subscriptions SET enddate = %s WHERE id = %s", (enddate, existing_subscription['id']))
        else:
            # Create new subscription
            vercel_sql.execute("INSERT INTO subscriptions (user_id, order_id, amount, plan_id, pay_token, enddate, is_active) VALUES (%s, %s, %s, %s, %s, %s, TRUE)", (user_id, order_id, amount, plan_id, pay_token, enddate))
        
        return jsonify({"message": "Subscription updated successfully"}), 201
    except Exception as e:
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

@app.route('/check_subscription', methods=['GET', 'POST'])
@cache.cached(timeout=50, key_prefix='check_subscription_')
def check_subscription():
    data = request.get_json()
    user_id = data.get('userId')
    plan_id = data.get('planId')

    try:
        subscription = vercel_sql.execute("SELECT * FROM subscriptions WHERE user_id = %s AND plan_id = %s AND is_active = TRUE AND enddate >= NOW()", (user_id, plan_id)).fetchone()
        
        if subscription:
            return jsonify({"is_subscribed": True, "enddate": subscription['enddate'].strftime('%Y-%m-%d')}), 200
        else:
            return jsonify({"is_subscribed": False}), 404
    except Exception as e:
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

@app.route('/delete_subscription/<int:subscription_id>', methods=['POST'])
def delete_subscription(subscription_id):
    try:
        vercel_sql.execute("DELETE FROM subscriptions WHERE id = %s", (subscription_id,))
        return jsonify({'message': 'Subscription deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': 'Subscription not found', 'error': str(e)}), 404

@app.route('/subscribers/list', methods=['GET'])
def list_subscribers_html():
    try:
        all_subscriptions = vercel_sql.execute("SELECT * FROM subscriptions WHERE is_active = TRUE").fetchall()
        return render_template('subscribers.html', subscriptions=all_subscriptions)
    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)
