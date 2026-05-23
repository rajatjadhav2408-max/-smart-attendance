import jwt
import datetime
from flask_bcrypt import Bcrypt
from functools import wraps
from flask import request, jsonify

bcrypt = Bcrypt()
SECRET_KEY = "smart-attendance-secret-key" # In production, use environment variable

def encode_auth_token(user_id):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    except Exception as e:
        return e

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
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['sub']
        except jwt.ExpiredSignatureError:
            print("Token expired")
            return jsonify({'message': 'Token is expired!'}), 401
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {str(e)}")
            return jsonify({'message': f'Token is invalid: {str(e)}'}), 401
        except Exception as e:
            print(f"Token error: {str(e)}")
            return jsonify({'message': 'Token error!'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated
