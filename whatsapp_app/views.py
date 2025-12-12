from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import User, Contact, Message, Group, GroupMembership, GroupMessage
from .serializers import ContactSerializer, MessageSerializer, GroupSerializer, GroupMembershipSerializer, GroupMessageSerializer
from django.utils import timezone
from datetime import timedelta
import random

class RegisterView(APIView):
    def post(self, request):
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        mobile_number = request.data.get('mobile_number')
        password = request.data.get('password')
        
        # Check if user already exists
        if User.objects.filter(mobile_number=mobile_number).exists():
            return Response({
                "error": "User already exists with this mobile number",
                "message": "Please login instead",
                "status": "user_exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(
            username=mobile_number,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number
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
        
        # Fetch user's contacts (with error handling)
        try:
            contacts = Contact.objects.filter(user=user)
            contacts_data = [
                {
                    "id": contact.id,
                    "name": contact.name,
                    "mobile_number": contact.mobile_number
                }
                for contact in contacts
            ]
        except Exception as e:
            print(f"Error fetching contacts: {e}")
            contacts_data = []
        
        # Add user's own info as contact if no contacts exist
        if not contacts_data:
            contacts_data.append({
                "id": 0,  # Special ID for user's own contact
                "name": f"{user.first_name} {user.last_name}".strip(),
                "mobile_number": user.mobile_number
            })
        
        return Response({
            "message": "User registered successfully",
            "otp": otp_code,  # Remove this in production
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "status": "registered",
            "contacts": contacts_data,
            "contacts_count": len(contacts_data)
        }, status=status.HTTP_201_CREATED)


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
                status=status.HTTP_404_NOT_FOUND
            )


class FetchAllUsersView(APIView):
    """
    API to fetch all users for group chat
    GET /api/users/ - Fetch all registered users
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
            
            # Get all users
            all_users = User.objects.all()
            
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
                "message": "Users fetched successfully",
                "count": len(users_data),
                "users": users_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch users: {str(e)}"}, 
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