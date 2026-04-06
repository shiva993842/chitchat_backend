import os
import sys
import django

# Add the project path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp.settings')
django.setup()

from whatsapp_app.models import User, FriendRequest
from django.db import transaction

def create_friend_requests():
    print("Creating friend requests between existing users...")
    
    # Get all unique users by ID
    users = User.objects.all().order_by('id')
    created_count = 0
    
    with transaction.atomic():
        # Clear existing friend requests first
        FriendRequest.objects.all().delete()
        print("Cleared existing friend requests")
        
        # Create friend requests between each pair of users
        for i, user in enumerate(users):
            for j in range(i + 1, len(users)):
                other_user = users[j]
                
                # Create friend request from user to other_user
                FriendRequest.objects.create(
                    sender=user,
                    receiver=other_user,
                    status='PENDING'
                )
                created_count += 1
                print(f'Created friend request: {user.first_name} (ID:{user.id}) -> {other_user.first_name} (ID:{other_user.id})')
    
    print(f'\nSuccessfully created {created_count} friend requests between existing users')

if __name__ == '__main__':
    create_friend_requests()
