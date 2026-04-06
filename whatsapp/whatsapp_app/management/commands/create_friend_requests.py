from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from whatsapp_app.models import User, FriendRequest


class Command(BaseCommand):
    help = 'Create friend requests between all existing users who do not have them'

    def handle(self, *args, **options):
        self.stdout.write('Creating friend requests between existing users...')
        
        users = User.objects.all()
        created_count = 0
        
        with transaction.atomic():
            # Create combinations of user pairs (avoid duplicates and self-requests)
            for i, user in enumerate(users):
                for other_user in users[i+1:]:  # Start from i+1 to avoid duplicates
                    # Check if friend request already exists in either direction
                    existing_request = FriendRequest.objects.filter(
                        models.Q(sender=user, receiver=other_user) |
                        models.Q(sender=other_user, receiver=user)
                    ).exists()
                    
                    if not existing_request:
                        # Create friend request from user to other_user
                        FriendRequest.objects.create(
                            sender=user,
                            receiver=other_user,
                            status='PENDING'
                        )
                        created_count += 1
                        self.stdout.write(
                            f'Created friend request: {user.first_name} -> {other_user.first_name}'
                        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} friend requests between existing users'
            )
        )
