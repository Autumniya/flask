import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://default:B8bPQYm9vEuj@ep-green-term-a4aolss4.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Configure Redis
redis_client = Redis(host='redis-12217.c327.europe-west1-2.gce.cloud.redislabs.com', port=12217, password='DonniyaMali223', decode_responses=True)  # Adjust for your Redis setup
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), nullable=False)
    order_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    plan_id = db.Column(db.String(255), nullable=False)
    pay_token = db.Column(db.String(255), nullable=False)
    subscription_date = db.Column(db.DateTime, default=datetime.utcnow)
    enddate = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
# Database initialization function
def initialize_db():
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    user_id = data.get('userId')
    plan_id = data.get('planId')
    enddate = datetime.strptime(data.get('end_date'), '%d-%B-%Y')

    existing_subscription = Subscription.query.filter_by(user_id=user_id, plan_id=plan_id, is_active=True).first()

    if existing_subscription:
        existing_subscription.enddate = enddate
        db.session.commit()
        # Use a combination of userId and planId as the Redis key
        redis_key = f"{user_id}:{plan_id}:{enddate}"
        redis_client.set(redis_key, 'active')
        return jsonify({"message": "Subscription updated successfully"}), 201
    else:
        new_subscription = Subscription(
            user_id=user_id,
            order_id=data.get('orderId'),
            amount=data.get('amount'),
            plan_id=plan_id,
            pay_token=data.get('pay_token'),
            enddate=enddate,
            is_active=True
        )
        db.session.add(new_subscription)
        db.session.commit()
        redis_key = f"{user_id}:{plan_id}:{enddate}"
        redis_client.set(redis_key, 'active')
        return jsonify({"message": "Subscription added successfully"}), 201

@app.route('/check_subscription', methods=['POST'])
def check_subscription():
    user_id = request.json.get('userId')
    plan_id = request.json.get('planId')
    enddate = request.json.get('end_date')

    # Use the combination of userId and planId to check the subscription status in Redis
    redis_key = f"{user_id}:{plan_id}:{enddate}"
    status = redis_client.get(redis_key)

    if status == 'active':
        # If found in Redis cache, return the cached status without querying the database
        # Assume Redis also stores the enddate or fetch it from DB if necessary
        enddate = redis_client.get(f"{redis_key}:enddate")  # This might require storing the end date in Redis as well
        if not enddate:  # If end_date is not found in Redis, consider fetching it from the database
            subscription = Subscription.query.filter_by(user_id=user_id, plan_id=plan_id, is_active=True).first()
            enddate = subscription.enddate.strftime('%Y-%m-%d') if subscription else None
        return jsonify({"is_subscribed": True, "enddate": enddate}), 201
    else:
        # If not found in Redis, query the database and update the Redis cache accordingly
        subscription = Subscription.query.filter(Subscription.user_id == user_id, Subscription.plan_id == plan_id, Subscription.is_active == True, Subscription.enddate >= datetime.utcnow()).first()
        if subscription:
            redis_client.set(redis_key, 'active')  # Refresh or set cache entry
            redis_client.set(f"{redis_key}:enddate", subscription.enddate.strftime('%Y-%m-%d'))  # Optionally cache the end date as well
            return jsonify({"is_subscribed": True, "enddate": subscription.enddate.strftime('%Y-%m-%d')}), 200
        else:
            return jsonify({"is_subscribed": False}), 404

@app.route('/delete_subscription/<int:subscription_id>', methods=['POST'])
def delete_subscription(subscription_id):
    subscription = Subscription.query.get(subscription_id)
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
        return jsonify({'message': 'Subscription deleted successfully'}), 200
    else:
        return jsonify({'message': 'Subscription not found'}), 404

@app.route('/subscribers/list', methods=['GET'])
def list_subscribers_html():
    all_subscriptions = Subscription.query.filter(Subscription.is_active == True).all()
    return render_template('subscribers.html', subscriptions=all_subscriptions)

initialize_db()
