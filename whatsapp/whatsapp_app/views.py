from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User as DjangoUser
from django.utils import timezone
from datetime import timedelta
import random
from django.db import models
from .models import User, Contact, Message, Group, GroupMembership, GroupMessage, FriendRequest
from .serializers import ContactSerializer, MessageSerializer, GroupMessageSerializer


class LoginView(APIView):
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        
        try:
            user = User.objects.get(mobile_number=mobile_number)
            
            # Generate 6 digit OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Save OTP to user
            user.otp = otp_code
            user.otp_created_at = timezone.now()
            user.save()
            
            # Print OTP in console (for testing)
            print(f"\n{'='*40}")
            print(f"OTP for {mobile_number}: {otp_code}")
            print(f"{'='*40}\n")
            
            # Fetch user's contacts
            contacts = Contact.objects.filter(user=user)
            contacts_data = [
                {
                    "id": contact.id,
                    "name": contact.name,
                    "mobile_number": contact.mobile_number
                }
                for contact in contacts
            ]
            
            # Add user's own info as contact if no contacts exist
            if not contacts_data:
                contacts_data.append({
                    "id": 0,  # Special ID for user's own contact
                    "name": f"{user.first_name} {user.last_name}".strip(),
                    "mobile_number": user.mobile_number
                })
            
            return Response({
                "message": "OTP sent successfully",
                "otp": otp_code,  # Remove this in production
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "mobile_number": user.mobile_number,
                "contacts": contacts_data,
                "contacts_count": len(contacts_data)
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"error": "User not found. Please register first."}, status=status.HTTP_404_NOT_FOUND)


class RegisterView(APIView):
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        password = request.data.get('password')
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        
        if not all([mobile_number, password, email, first_name, last_name]):
            return Response(
                {"error": "All fields are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(mobile_number=mobile_number).exists():
            return Response(
                {"error": "User with this mobile number already exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.create_user(
                username=mobile_number,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                mobile_number=mobile_number
            )
            
            # Auto-send friend requests from new user to all existing users (one-way)
            existing_users = User.objects.exclude(id=user.id)
            for existing_user in existing_users:
                FriendRequest.objects.get_or_create(
                    sender=user,  # New user sends the request
                    receiver=existing_user,  # Existing user receives the request
                    defaults={'status': 'PENDING'}
                )
            
            # Generate 6 digit OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Save OTP to user
            user.otp = otp_code
            user.otp_created_at = timezone.now()
            user.save()
            
            # Print OTP in console (for testing)
            print(f"\n{'='*40}")
            print(f"OTP for {mobile_number}: {otp_code}")
            print(f"{'='*40}\n")
            
            return Response({
                "message": "User registered successfully",
                "otp": otp_code,  # Remove this in production
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "mobile_number": user.mobile_number,
                "contacts": [],  # Empty contacts for new user
                "contacts_count": 0
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to register user: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyOTPView(APIView):
    def post(self, request):
        mobile_number = request.data.get('mobile_number')
        otp_code = request.data.get('otp')
        
        try:
            user = User.objects.get(mobile_number=mobile_number)
            
            # Check if OTP matches
            if user.otp != otp_code:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if OTP expired (5 minutes validity)
            if user.otp_created_at:
                otp_age = timezone.now() - user.otp_created_at
                if otp_age > timedelta(minutes=5):
                    return Response({"error": "OTP expired. Please request new OTP."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "No OTP found"}, status=status.HTTP_400_BAD_REQUEST)
            
            # OTP verified successfully
            user.otp = None  # Clear OTP after verification
            user.otp_created_at = None
            user.save()
            
            # Fetch user's contacts
            contacts = Contact.objects.filter(user=user)
            contacts_data = [
                {
                    "id": contact.id,
                    "name": contact.name,
                    "mobile_number": contact.mobile_number
                }
                for contact in contacts
            ]
            
            # Add user's own info as contact if no contacts exist
            if not contacts_data:
                contacts_data.append({
                    "id": 0,  # Special ID for user's own contact
                    "name": f"{user.first_name} {user.last_name}".strip(),
                    "mobile_number": user.mobile_number
                })
            
            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "mobile_number": user.mobile_number,
                "contacts": contacts_data,
                "contacts_count": len(contacts_data)
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


class FetchContactsView(APIView):
    """
    API to fetch all contacts for a logged-in user
    GET /api/contacts/ - Fetch all contacts with names
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            contacts = Contact.objects.filter(user=user).order_by('-created_at')
            serializer = ContactSerializer(contacts, many=True)
            
            # Convert to list format
            contacts_data = serializer.data
            
            # Add user's own info as contact if no contacts exist
            if not contacts_data:
                contacts_data = [{
                    "id": 0,  # Special ID for user's own contact
                    "name": f"{user.first_name} {user.last_name}".strip(),
                    "mobile_number": user.mobile_number,
                    "created_at": user.date_joined.isoformat(),
                    "updated_at": user.date_joined.isoformat()
                }]
            
            return Response({
                "message": "Contacts fetched successfully",
                "count": len(contacts_data),
                "contacts": contacts_data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AddContactView(APIView):
    """
    API to add a new contact for a user
    POST /api/contacts/add/ - Add a new contact
    """
    def post(self, request):
        user_id = request.data.get('user_id')
        name = request.data.get('name')
        mobile_number = request.data.get('mobile_number')
        
        # Validate required fields
        if not all([user_id, name, mobile_number]):
            return Response(
                {"error": "user_id, name, and mobile_number are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            # Check if contact already exists
            if Contact.objects.filter(user=user, mobile_number=mobile_number).exists():
                return Response(
                    {"error": "Contact with this mobile number already exists"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new contact
            contact = Contact.objects.create(
                user=user,
                name=name,
                mobile_number=mobile_number
            )
            
            serializer = ContactSerializer(contact)
            return Response({
                "message": "Contact added successfully",
                "contact": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class DeleteContactView(APIView):
    """
    API to delete a contact
    DELETE /api/contacts/delete/ - Delete a contact
    """
    def delete(self, request):
        contact_id = request.query_params.get('contact_id')
        user_id = request.data.get('user_id')
        
        if not contact_id or not user_id:
            return Response(
                {"error": "contact_id and user_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            contact = Contact.objects.get(id=contact_id, user=user)
            contact.delete()
            
            return Response({
                "message": "Contact deleted successfully"
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Contact.DoesNotExist:
            return Response(
                {"error": "Contact not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class FetchAllUsersView(APIView):
    """
    API to fetch all friends for a user (only accepted friend requests)
    GET /api/users/?current_user_id=7 - Fetch all accepted friends
    """
    def get(self, request):
        try:
            # Get current user ID (required)
            current_user_id = request.query_params.get('current_user_id')
            
            if not current_user_id:
                return Response(
                    {"error": "current_user_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get current user
            current_user = User.objects.get(id=current_user_id)
            
            # Get all accepted friend requests (both sent and received)
            accepted_friends = User.objects.filter(
                models.Q(
                    # Friends where current user sent the request and it was accepted
                    id__in=FriendRequest.objects.filter(
                        sender=current_user, 
                        status='ACCEPTED'
                    ).values_list('receiver_id', flat=True)
                ) | models.Q(
                    # Friends where current user received the request and accepted it
                    id__in=FriendRequest.objects.filter(
                        receiver=current_user, 
                        status='ACCEPTED'
                    ).values_list('sender_id', flat=True)
                )
            ).distinct()
            
            # Include current user in the list
            all_users = accepted_friends.union(User.objects.filter(id=current_user.id))
            
            users_data = []
            for user in all_users:
                # Convert profile picture URL to full URL if exists
                profile_picture_url = user.profile_picture_url
                if profile_picture_url and not profile_picture_url.startswith('http'):
                    profile_picture_url = f"http://10.0.2.2:8000{profile_picture_url}"
                
                user_data = {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "email": user.email,
                    "mobile_number": user.mobile_number,
                    "date_joined": user.date_joined.isoformat(),
                    "is_owner": user.id == int(current_user_id),
                    "profile_picture_url": profile_picture_url
                }
                users_data.append(user_data)
            
            return Response({
                "message": "Friends fetched successfully",
                "count": len(users_data),
                "users": users_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch friends: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FetchAllGroupsView(APIView):
    """
    API to fetch all group chats for a user
    GET /api/groups/ - Fetch all groups the user is a member of
    """
    def get(self, request):
        try:
            # Get current user ID (required)
            current_user_id = request.query_params.get('current_user_id')
            
            if not current_user_id:
                return Response(
                    {"error": "current_user_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user and their groups
            user = User.objects.get(id=current_user_id)
            groups = Group.objects.filter(members=user, is_active=True)
            
            groups_data = []
            for group in groups:
                # Get member count
                member_count = group.members.count()
                
                # Get last message (if any)
                last_message = GroupMessage.objects.filter(group=group).first()
                
                # Check if user is admin
                is_admin = GroupMembership.objects.filter(group=group, user=user, is_admin=True).exists()
                
                groups_data.append({
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "admin_id": group.admin.id,
                    "admin_name": f"{group.admin.first_name} {group.admin.last_name}".strip(),
                    "member_count": member_count,
                    "is_admin": is_admin,
                    "created_at": group.created_at.isoformat(),
                    "updated_at": group.updated_at.isoformat(),
                    "last_message": {
                        "content": last_message.content,
                        "sender": f"{last_message.sender.first_name} {last_message.sender.last_name}".strip(),
                        "timestamp": last_message.timestamp.isoformat()
                    } if last_message else None
                })
            
            return Response({
                "message": "Groups fetched successfully",
                "count": len(groups_data),
                "groups": groups_data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch groups: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetUnreadGroupMessagesView(APIView):
    """
    API to get unread group messages for a user
    GET /api/groups/messages/unread/?user_id=1 - Get unread group messages
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            # Get all groups the user is a member of
            user_groups = Group.objects.filter(members=user, is_active=True)
            
            # Get unread group messages
            unread_messages = []
            for group in user_groups:
                messages = GroupMessage.objects.filter(
                    group=group,
                    is_read=False
                ).exclude(sender=user).order_by('-timestamp')
                
                for message in messages:
                    unread_messages.append({
                        "id": message.id,
                        "sender": message.sender.id,
                        "group": message.group.id,
                        "sender_name": f"{message.sender.first_name} {message.sender.last_name}".strip(),
                        "group_name": message.group.name,
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat(),
                        "is_read": message.is_read
                    })
            
            # Sort by timestamp (most recent first)
            unread_messages.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return Response({
                "message": "Unread group messages fetched successfully",
                "count": len(unread_messages),
                "messages": unread_messages
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch unread group messages: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkGroupMessagesAsReadView(APIView):
    """
    API to mark group messages as read
    POST /api/groups/messages/mark-read/ - Mark group messages as read
    """
    def post(self, request):
        user_id = request.data.get('user_id')
        group_id = request.data.get('group_id')
        
        if not all([user_id, group_id]):
            return Response(
                {"error": "user_id and group_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(id=group_id)
            
            # Check if user is a member of the group
            if not group.members.filter(id=user.id).exists():
                return Response(
                    {"error": "User is not a member of this group"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Mark all unread messages in the group as read (excluding user's own messages)
            updated_count = GroupMessage.objects.filter(
                group=group,
                is_read=False
            ).exclude(sender=user).update(is_read=True)
            
            return Response({
                "message": "Messages marked as read successfully",
                "messages_updated": updated_count
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return Response(
                {"error": "Group not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to mark messages as read: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SendMessageView(APIView):
    """
    API to send a message to another user
    POST /api/messages/send/ - Send message
    """
    def post(self, request):
        sender_id = request.data.get('sender_id')
        receiver_id = request.data.get('receiver_id')
        content = request.data.get('content')
        
        # Validate required fields
        if not all([sender_id, receiver_id, content]):
            return Response(
                {"error": "sender_id, receiver_id, and content are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
            
            # Create message
            message = Message.objects.create(
                sender=sender,
                receiver=receiver,
                content=content
            )
            
            serializer = MessageSerializer(message)
            
            return Response({
                "message": "Message sent successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Sender or receiver not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GetMessagesView(APIView):
    """
    API to get messages between two users
    GET /api/messages/?user_id=1&other_user_id=2 - Get conversation
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        other_user_id = request.query_params.get('other_user_id')
        
        if not user_id or not other_user_id:
            return Response(
                {"error": "user_id and other_user_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            other_user = User.objects.get(id=other_user_id)
            
            # Get messages between these two users
            messages = Message.objects.filter(
                (models.Q(sender=user, receiver=other_user) | 
                 models.Q(sender=other_user, receiver=user))
            ).order_by('timestamp')
            
            serializer = MessageSerializer(messages, many=True)
            
            # Mark messages as read
            Message.objects.filter(
                sender=other_user, 
                receiver=user, 
                is_read=False
            ).update(is_read=True)
            
            return Response({
                "message": "Messages fetched successfully",
                "count": messages.count(),
                "messages": serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GetUnreadMessagesView(APIView):
    """
    API to get unread messages for a user
    GET /api/messages/unread/?user_id=1 - Get unread messages
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            # Get unread messages
            messages = Message.objects.filter(
                receiver=user, 
                is_read=False
            ).order_by('-timestamp')
            
            serializer = MessageSerializer(messages, many=True)
            
            return Response({
                "message": "Unread messages fetched successfully",
                "count": messages.count(),
                "messages": serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SendFriendRequestView(APIView):
    """
    API to send a friend request
    POST /api/friends/request/ - Send friend request
    """
    def post(self, request):
        sender_id = request.data.get('sender_id')
        receiver_id = request.data.get('receiver_id')
        
        if not all([sender_id, receiver_id]):
            return Response(
                {"error": "sender_id and receiver_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if sender_id == receiver_id:
            return Response(
                {"error": "Cannot send friend request to yourself"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
            
            # Check if friend request already exists
            existing_request = FriendRequest.objects.filter(
                sender=sender, 
                receiver=receiver
            ).first()
            
            if existing_request:
                if existing_request.status == 'PENDING':
                    return Response(
                        {"error": "Friend request already sent and pending"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif existing_request.status == 'ACCEPTED':
                    return Response(
                        {"error": "Already friends with this user"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:  # DECLINED
                    # Update the declined request to pending again
                    existing_request.status = 'PENDING'
                    existing_request.save()
                    return Response({
                        "message": "Friend request sent successfully",
                        "request_id": existing_request.id
                    }, status=status.HTTP_201_CREATED)
            
            # Create new friend request (one-way only)
            friend_request = FriendRequest.objects.create(
                sender=sender,
                receiver=receiver,
                status='PENDING'
            )
            
            return Response({
                "message": "Friend request sent successfully",
                "request_id": friend_request.id
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Sender or receiver not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class RespondToFriendRequestView(APIView):
    """
    API to accept or decline a friend request
    POST /api/friends/respond/ - Accept or decline friend request
    """
    def post(self, request):
        request_id = request.data.get('request_id')
        action = request.data.get('action')  # 'accept' or 'decline'
        
        if not all([request_id, action]):
            return Response(
                {"error": "request_id and action are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action not in ['accept', 'decline']:
            return Response(
                {"error": "action must be 'accept' or 'decline'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            friend_request = FriendRequest.objects.get(id=request_id)
            
            # If the request is no longer pending, return a 200 with current state
            # instead of treating it as a hard error. This avoids confusing toast
            # messages when the user taps the button multiple times or the state
            # was already updated elsewhere.
            if friend_request.status != 'PENDING':
                if friend_request.status == 'ACCEPTED':
                    return Response(
                        {
                            "message": "Friend request already accepted",
                            "request_id": friend_request.id,
                            "status": friend_request.status,
                            "is_mutual": False,
                            "reverse_request_id": None,
                            "new_status_text": "Wait for acceptance",
                        },
                        status=status.HTTP_200_OK,
                    )
                if friend_request.status == 'DECLINED':
                    return Response(
                        {
                            "message": "Friend request already declined",
                            "request_id": friend_request.id,
                            "status": friend_request.status,
                            "is_mutual": False,
                            "reverse_request_id": None,
                            "new_status_text": "Declined",
                        },
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {"error": "Friend request is no longer pending"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update status based on action
            if action == 'accept':
                # Check if reverse request exists and is already accepted
                reverse_request = FriendRequest.objects.filter(
                    sender=friend_request.receiver,
                    receiver=friend_request.sender
                ).first()
                
                if reverse_request and reverse_request.status == 'ACCEPTED':
                    # Both have accepted - make them friends
                    friend_request.status = 'ACCEPTED'
                    message = "Friend request accepted successfully - You are now friends!"
                    is_mutual = True
                    reverse_request_id = None
                    new_status_text = "Friends"
                else:
                    # First person accepting - create reverse request for second person to accept
                    friend_request.status = 'ACCEPTED'
                    is_mutual = False
                    if not reverse_request:
                        reverse_request = FriendRequest.objects.create(
                            sender=friend_request.receiver,
                            receiver=friend_request.sender,
                            status='PENDING'
                        )
                        reverse_request_id = reverse_request.id
                        message = "Friend request accepted! Waiting for the other person to accept your request."
                        new_status_text = "Wait for acceptance"
                    else:
                        reverse_request_id = reverse_request.id
                        message = "Friend request accepted! Waiting for the other person to accept your request."
                        new_status_text = "Wait for acceptance"
                
            else:  # decline
                friend_request.status = 'DECLINED'
                # Also decline the reverse request if it exists
                reverse_request = FriendRequest.objects.filter(
                    sender=friend_request.receiver,
                    receiver=friend_request.sender
                ).first()
                if reverse_request and reverse_request.status == 'PENDING':
                    reverse_request.status = 'DECLINED'
                    reverse_request.save()
                message = "Friend request declined"
                is_mutual = False
                reverse_request_id = None
                new_status_text = "Declined"
            
            friend_request.save()
            
            return Response({
                "message": message,
                "request_id": friend_request.id,
                "status": friend_request.status,
                "is_mutual": is_mutual,
                "reverse_request_id": reverse_request_id,
                "new_status_text": new_status_text
            }, status=status.HTTP_200_OK)
            
        except FriendRequest.DoesNotExist:
            return Response(
                {"error": "Friend request not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CancelFriendRequestView(APIView):
    """
    API to cancel a pending friend request (only if you sent it)
    POST /api/friends/cancel/ - Cancel a pending friend request
    """
    def post(self, request):
        try:
            request_id = request.data.get('request_id')
            user_id = request.data.get('user_id')  # ✅ NEW: User who wants to cancel
            
            if not request_id or not user_id:
                return Response(
                    {"error": "request_id and user_id are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            friend_request = FriendRequest.objects.get(id=request_id)
            user = User.objects.get(id=user_id)
            
            # Only allow cancellation of pending requests that YOU sent
            if friend_request.status != 'PENDING':
                return Response(
                    {"error": "Only pending friend requests can be cancelled"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if the current user is the sender
            if friend_request.sender != user:
                return Response(
                    {"error": "You can only cancel friend requests that you sent"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete the friend request
            friend_request.delete()
            
            return Response({
                "message": "Friend request cancelled successfully",
                "request_id": int(request_id)
            }, status=status.HTTP_200_OK)
            
        except FriendRequest.DoesNotExist:
            return Response(
                {"error": "Friend request not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


import logging
logger = logging.getLogger(__name__)

class GetPendingFriendRequestsView(APIView):
    """
    API to get pending friend requests for a user
    GET /api/friends/pending/?user_id=1 - Get pending friend requests
    """
    def get(self, request):
        try:
            logger.info("Starting GetPendingFriendRequestsView")
            
            user_id = request.GET.get('user_id')
            logger.info(f"Received user_id: {user_id}")
            
            if not user_id:
                logger.warning("user_id is required")
                return Response(
                    {"error": "user_id is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                user = User.objects.get(id=user_id)
                logger.info(f"Found user: {user.first_name} {user.last_name}")
            except User.DoesNotExist:
                logger.error(f"User not found with id: {user_id}")
                return Response(
                    {"error": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                logger.error(f"Error getting user: {str(e)}")
                return Response(
                    {"error": f"Error retrieving user: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            try:
                # Get all friend requests involving this user (sent or received)
                # Exclude self-requests (where sender=receiver) and declined requests
                all_requests = FriendRequest.objects.filter(
                    models.Q(sender=user) | models.Q(receiver=user)
                ).exclude(
                    models.Q(sender=user, receiver=user)  # Exclude self-requests
                ).exclude(
                    models.Q(status='DECLINED')  # Exclude cancelled/declined requests
                ).order_by('-created_at')
                
                logger.info(f"Found {all_requests.count()} total requests")
                
            except Exception as e:
                logger.error(f"Error querying friend requests: {str(e)}")
                return Response(
                    {"error": f"Error querying friend requests: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            requests_data = []
            seen_user_pairs = set()  # Track seen user pairs to avoid duplicates
            
            try:
                for req in all_requests:
                    # Create unique pair key (sorted user IDs to avoid duplicates)
                    user_pair_key = tuple(sorted([req.sender.id, req.receiver.id]))
                    
                    # Skip if we already processed this user pair
                    if user_pair_key in seen_user_pairs:
                        continue
                        
                    seen_user_pairs.add(user_pair_key)
                    
                    # Check if reverse request exists
                    reverse_request = FriendRequest.objects.filter(
                        sender=req.receiver,
                        receiver=req.sender
                    ).first()
                    
                    # Determine mutual friendship status
                    is_mutual = (req.status == 'ACCEPTED' and 
                                reverse_request and 
                                reverse_request.status == 'ACCEPTED')
                    
                    # Determine request direction and status text
                    is_sent_by_me = req.sender == user
                    status_text = req.status
                    
                    if is_sent_by_me and req.status == 'PENDING':
                        status_text = "Wait for acceptance"  # ✅ What sender sees
                    elif not is_sent_by_me and req.status == 'PENDING':
                        status_text = "Friend sent you a friend request"  # ✅ What receiver sees
                    elif req.status == 'ACCEPTED':
                        if is_mutual:
                            status_text = "Friends"
                        elif is_sent_by_me:
                            status_text = "Accepted"  # You accepted someone's request
                        else:
                            status_text = "Friend sent you a friend request"  # Someone accepted your request
                    elif req.status == 'DECLINED':
                        status_text = "Declined"
                    
                    # Determine which user to display (the other user, not the current user)
                    other_user = req.receiver if req.sender == user else req.sender
                    
                    # Safe profile picture URL handling
                    sender_profile_url = req.sender.profile_picture_url if hasattr(req.sender, 'profile_picture_url') and req.sender.profile_picture_url else None
                    receiver_profile_url = req.receiver.profile_picture_url if hasattr(req.receiver, 'profile_picture_url') and req.receiver.profile_picture_url else None
                    other_user_profile_url = other_user.profile_picture_url if hasattr(other_user, 'profile_picture_url') and other_user.profile_picture_url else None
                    
                    request_data = {
                        "id": req.id,
                        "sender": {
                            "id": req.sender.id,
                            "first_name": req.sender.first_name if hasattr(req.sender, 'first_name') else "",
                            "last_name": req.sender.last_name if hasattr(req.sender, 'last_name') else "",
                            "full_name": f"{req.sender.first_name if hasattr(req.sender, 'first_name') else ''} {req.sender.last_name if hasattr(req.sender, 'last_name') else ''}".strip(),
                            "mobile_number": req.sender.mobile_number if hasattr(req.sender, 'mobile_number') else "",
                            "profile_picture_url": sender_profile_url
                        },
                        "receiver": {
                            "id": req.receiver.id,
                            "first_name": req.receiver.first_name if hasattr(req.receiver, 'first_name') else "",
                            "last_name": req.receiver.last_name if hasattr(req.receiver, 'last_name') else "",
                            "full_name": f"{req.receiver.first_name if hasattr(req.receiver, 'first_name') else ''} {req.receiver.last_name if hasattr(req.receiver, 'last_name') else ''}".strip(),
                            "mobile_number": req.receiver.mobile_number if hasattr(req.receiver, 'mobile_number') else "",
                            "profile_picture_url": receiver_profile_url
                        },
                        "other_user": {  # ✅ IMPORTANT: Use this field to avoid duplicates
                            "id": other_user.id,
                            "first_name": other_user.first_name if hasattr(other_user, 'first_name') else "",
                            "last_name": other_user.last_name if hasattr(other_user, 'last_name') else "",
                            "full_name": f"{other_user.first_name if hasattr(other_user, 'first_name') else ''} {other_user.last_name if hasattr(other_user, 'last_name') else ''}".strip(),
                            "mobile_number": other_user.mobile_number if hasattr(other_user, 'mobile_number') else "",
                            "profile_picture_url": other_user_profile_url
                        },
                        "status": req.status,
                        "status_text": status_text,  # ✅ Human-readable status
                        "is_sent_by_me": is_sent_by_me,  # ✅ Direction indicator
                        "created_at": req.created_at.isoformat() if hasattr(req, 'created_at') else "",
                        "has_reverse_request": reverse_request is not None,
                        "reverse_request_status": reverse_request.status if reverse_request else None,
                        "is_mutual": is_mutual
                    }
                    requests_data.append(request_data)
                
                logger.info(f"Successfully processed {len(requests_data)} unique requests")
                
            except Exception as e:
                logger.error(f"Error processing requests: {str(e)}")
                return Response(
                    {"error": f"Error processing requests: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                "message": "Pending friend requests retrieved successfully",
                "count": len(requests_data),
                "requests": requests_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error in GetPendingFriendRequestsView: {str(e)}")
            return Response(
                {"error": f"Internal server error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
