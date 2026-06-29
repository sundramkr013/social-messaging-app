from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Message, Conversation, User
from datetime import datetime

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('', methods=['GET'])
@jwt_required()
def get_messages():
    """Get all messages for current user"""
    user_id = get_jwt_identity()
    receiver_id = request.args.get('receiver_id', type=int)
    
    if receiver_id:
        # Get messages between two specific users
        messages = Message.query.filter(
            ((Message.sender_id == user_id) & (Message.receiver_id == receiver_id)) |
            ((Message.sender_id == receiver_id) & (Message.receiver_id == user_id))
        ).order_by(Message.created_at.asc()).all()
    else:
        # Get all messages for current user
        messages = Message.query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).order_by(Message.created_at.desc()).all()
    
    return jsonify([msg.to_dict() for msg in messages]), 200

@messages_bp.route('/<int:message_id>', methods=['GET'])
@jwt_required()
def get_message(message_id):
    """Get a specific message"""
    user_id = get_jwt_identity()
    message = Message.query.get(message_id)
    
    if not message:
        return jsonify({'message': 'Message not found'}), 404
    
    # Check if user is sender or receiver
    if message.sender_id != user_id and message.receiver_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(message.to_dict()), 200

@messages_bp.route('', methods=['POST'])
@jwt_required()
def send_message():
    """Send a new message"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not all(k in data for k in ('receiver_id', 'content')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    receiver_id = data['receiver_id']
    
    # Check if receiver exists
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'message': 'Receiver not found'}), 404
    
    # Create message
    message = Message(
        sender_id=user_id,
        receiver_id=receiver_id,
        content=data['content']
    )
    
    db.session.add(message)
    
    # Update or create conversation
    conversation = Conversation.query.filter_by(
        user_id=user_id,
        contact_id=receiver_id
    ).first()
    
    if not conversation:
        conversation = Conversation(
            user_id=user_id,
            contact_id=receiver_id
        )
        db.session.add(conversation)
    
    conversation.last_message = data['content']
    conversation.last_message_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Message sent successfully',
        'data': message.to_dict()
    }), 201

@messages_bp.route('/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(message_id):
    """Mark message as read"""
    user_id = get_jwt_identity()
    message = Message.query.get(message_id)
    
    if not message:
        return jsonify({'message': 'Message not found'}), 404
    
    if message.receiver_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    message.is_read = True
    db.session.commit()
    
    return jsonify(message.to_dict()), 200

@messages_bp.route('/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(message_id):
    """Delete a message"""
    user_id = get_jwt_identity()
    message = Message.query.get(message_id)
    
    if not message:
        return jsonify({'message': 'Message not found'}), 404
    
    if message.sender_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({'message': 'Message deleted successfully'}), 200

@messages_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get all conversations for current user"""
    user_id = get_jwt_identity()
    conversations = Conversation.query.filter_by(user_id=user_id).order_by(
        Conversation.last_message_at.desc()
    ).all()
    
    return jsonify([conv.to_dict() for conv in conversations]), 200