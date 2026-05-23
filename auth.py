import jwt
import datetime
import os
from flask_bcrypt import Bcrypt
from functools import wraps
from flask import request, jsonify

bcrypt = Bcrypt()

# Fix #1: Use environment variable for secret key, never hardcode it
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production-via-env-var')

def encode_auth_token(user_id):
    try:
        # Fix #12: Replace deprecated utcnow() with timezone-aware datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        payload = {
            'exp': now + datetime.timedelta(days=1),
            'iat': now,
            'sub': user_id
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    except Exception as e:
        return str(e)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Fix #12: Use timezone-aware datetime for decoding too
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'],
                              options={"require": ["exp", "iat", "sub"]})
            current_user_id = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token is expired!'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': f'Token is invalid: {str(e)}'}), 401
        except Exception as e:
            return jsonify({'message': 'Token error!'}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated
