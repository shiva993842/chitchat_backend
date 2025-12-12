from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Group, GroupMembership, GroupMessage
from .serializers import GroupSerializer, GroupMembershipSerializer, GroupMessageSerializer

class CreateGroupView(APIView):
    """
    API to create a new group chat
    POST /api/groups/create/ - Create group
    """
    def post(self, request):
        name = request.data.get('name')
        description = request.data.get('description', '')
        admin_id = request.data.get('admin_id')
        member_ids = request.data.get('member_ids', [])  # List of user IDs to add as members
        
        # Validate required fields
        if not all([name, admin_id]):
            return Response(
                {"error": "name and admin_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            admin = User.objects.get(id=admin_id)
            
            # Create group
            group = Group.objects.create(
                name=name,
                description=description,
                admin=admin
            )
            
            # Add admin as member
            GroupMembership.objects.create(
                group=group,
                user=admin,
                is_admin=True
            )
            
            # Add other members if provided
            if member_ids:
                for member_id in member_ids:
                    try:
                        member = User.objects.get(id=member_id)
                        if member != admin:  # Don't add admin again
                            GroupMembership.objects.create(
                                group=group,
                                user=member,
                                is_admin=False
                            )
                    except User.DoesNotExist:
                        continue  # Skip invalid user IDs
            
            serializer = GroupSerializer(group)
            return Response({
                "message": "Group created successfully",
                "group": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Admin user not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AddGroupMembersView(APIView):
    """
    API to add members to an existing group
    POST /api/groups/add-members/ - Add members to group
    """
    def post(self, request):
        group_id = request.data.get('group_id')
        member_ids = request.data.get('member_ids', [])
        requesting_user_id = request.data.get('requesting_user_id')
        
        # Validate required fields
        if not all([group_id, member_ids, requesting_user_id]):
            return Response(
                {"error": "group_id, member_ids, and requesting_user_id are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
            requesting_user = User.objects.get(id=requesting_user_id)
            
            # Check if requesting user is admin
            try:
                membership = GroupMembership.objects.get(group=group, user=requesting_user)
                if not membership.is_admin and group.admin != requesting_user:
                    return Response(
                        {"error": "Only group admins can add members"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except GroupMembership.DoesNotExist:
                return Response(
                    {"error": "You are not a member of this group"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            added_members = []
            for member_id in member_ids:
                try:
                    member = User.objects.get(id=member_id)
                    # Check if already a member
                    if not GroupMembership.objects.filter(group=group, user=member).exists():
                        GroupMembership.objects.create(
                            group=group,
                            user=member,
                            is_admin=False
                        )
                        added_members.append({
                            "id": member.id,
                            "name": f"{member.first_name} {member.last_name}".strip(),
                            "mobile_number": member.mobile_number
                        })
                except User.DoesNotExist:
                    continue
            
            return Response({
                "message": f"Added {len(added_members)} members to group",
                "added_members": added_members
            }, status=status.HTTP_200_OK)
            
        except Group.DoesNotExist:
            return Response(
                {"error": "Group not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GetUserGroupsView(APIView):
    """
    API to get all groups for a user
    GET /api/groups/user/?user_id=1 - Get user's groups
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
            groups = Group.objects.filter(members=user).order_by('-created_at')
            serializer = GroupSerializer(groups, many=True)
            
            return Response({
                "message": "Groups fetched successfully",
                "count": groups.count(),
                "groups": serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SendGroupMessageView(APIView):
    """
    API to send a message to a group
    POST /api/groups/send-message/ - Send group message
    """
    def post(self, request):
        group_id = request.data.get('group_id')
        sender_id = request.data.get('sender_id')
        content = request.data.get('content')
        
        # Validate required fields
        if not all([group_id, sender_id, content]):
            return Response(
                {"error": "group_id, sender_id, and content are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
            sender = User.objects.get(id=sender_id)
            
            # Check if sender is a member of the group
            if not GroupMembership.objects.filter(group=group, user=sender).exists():
                return Response(
                    {"error": "You are not a member of this group"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create message
            message = GroupMessage.objects.create(
                group=group,
                sender=sender,
                content=content
            )
            
            serializer = GroupMessageSerializer(message)
            return Response({
                "message": "Group message sent successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Group.DoesNotExist:
            return Response(
                {"error": "Group not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class GetGroupMessagesView(APIView):
    """
    API to get messages from a group
    GET /api/groups/messages/?group_id=1 - Get group messages
    """
    def get(self, request):
        group_id = request.query_params.get('group_id')
        
        if not group_id:
            return Response(
                {"error": "group_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
            messages = GroupMessage.objects.filter(group=group).order_by('timestamp')
            serializer = GroupMessageSerializer(messages, many=True)
            
            return Response({
                "message": "Group messages fetched successfully",
                "count": messages.count(),
                "messages": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Group.DoesNotExist:
            return Response(
                {"error": "Group not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
