from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Contact, Message, Group, GroupMembership, GroupMessage

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'mobile_number', 'password']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['mobile_number'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            mobile_number=validated_data['mobile_number']
        )
        return user

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'mobile_number', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'receiver', 'sender_name', 'receiver_name', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp']
    
    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
    
    def get_receiver_name(self, obj):
        return f"{obj.receiver.first_name} {obj.receiver.last_name}".strip()

class GroupSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'admin', 'admin_name', 'member_count', 'members', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_admin_name(self, obj):
        return f"{obj.admin.first_name} {obj.admin.last_name}".strip()
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_members(self, obj):
        members = obj.members.all()
        return [
            {
                "id": member.id,
                "name": f"{member.first_name} {member.last_name}".strip(),
                "mobile_number": member.mobile_number,
                "is_admin": GroupMembership.objects.get(group=obj, user=member).is_admin
            }
            for member in members
        ]

class GroupMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMembership
        fields = ['id', 'group', 'user', 'user_name', 'group_name', 'joined_at', 'is_admin']
        read_only_fields = ['id', 'joined_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def get_group_name(self, obj):
        return obj.group.name

class GroupMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMessage
        fields = ['id', 'group', 'sender', 'sender_name', 'group_name', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'timestamp']
    
    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip()
    
    def get_group_name(self, obj):
        return obj.group.name
