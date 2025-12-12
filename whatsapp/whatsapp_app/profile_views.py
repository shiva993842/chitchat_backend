from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import os
from django.conf import settings
from .models import User


class ViewProfileView(APIView):
    """
    API to view user profile
    GET /api/profile/{user_id} - Get user profile details
    """
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Check if this is the current user (owner)
            current_user_id = request.query_params.get('current_user_id')
            is_owner = current_user_id and int(current_user_id) == user.id
            
            # Convert profile picture URL to full URL if exists
            profile_picture_url = user.profile_picture_url
            if profile_picture_url and not profile_picture_url.startswith('http'):
                profile_picture_url = f"http://10.0.2.2:8000{profile_picture_url}"
            
            return Response({
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "mobile_number": user.mobile_number,
                "profile_picture_url": profile_picture_url,
                "bio": user.bio,
                "is_owner": is_owner,
                "date_joined": user.date_joined.isoformat()
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch profile: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateProfileView(APIView):
    """
    API to update user profile
    PUT/PATCH /api/profile/update/{user_id} - Update user profile
    """
    def put(self, request, user_id):
        return self._update_profile(request, user_id)
    
    def patch(self, request, user_id):
        return self._update_profile(request, user_id)
    
    def _update_profile(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Update fields if provided
            if 'first_name' in request.data:
                user.first_name = request.data['first_name']
            if 'last_name' in request.data:
                user.last_name = request.data['last_name']
            if 'email' in request.data:
                user.email = request.data['email']
            if 'bio' in request.data:
                user.bio = request.data['bio']
            if 'profile_picture_url' in request.data:
                user.profile_picture_url = request.data['profile_picture_url']
            
            user.save()
            
            # Convert profile picture URL to full URL if exists
            profile_picture_url = user.profile_picture_url
            if profile_picture_url and not profile_picture_url.startswith('http'):
                profile_picture_url = f"http://10.0.2.2:8000{profile_picture_url}"
            
            return Response({
                "message": "Profile updated successfully",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "mobile_number": user.mobile_number,
                    "profile_picture_url": profile_picture_url,
                    "bio": user.bio,
                    "date_joined": user.date_joined.isoformat()
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to update profile: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadProfilePictureView(APIView):
    """
    API to upload profile picture
    POST /api/profile/upload-picture/{user_id}/ - Upload profile picture
    """
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Validate file is provided - check multiple possible field names
            file_field_names = ['profile_picture', 'image', 'file', 'photo', 'picture']
            file = None
            field_used = None
            
            for field_name in file_field_names:
                if field_name in request.FILES:
                    file = request.FILES[field_name]
                    field_used = field_name
                    break
            
            if not file:
                return Response(
                    {"error": "No profile picture file provided. Available files: " + str(list(request.FILES.keys()))}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if file.content_type not in allowed_types:
                return Response(
                    {"error": "Invalid file type. Only JPEG, PNG, and WebP are allowed"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file size (5MB max)
            if file.size > 5 * 1024 * 1024:
                return Response(
                    {"error": "File too large. Maximum size is 5MB"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create profiles directory if it doesn't exist
            profiles_dir = os.path.join(settings.BASE_DIR, 'media', 'profiles')
            os.makedirs(profiles_dir, exist_ok=True)
            
            # Generate unique filename
            file_extension = os.path.splitext(file.name)[1]
            filename = f"user_{user_id}{file_extension}"
            filepath = os.path.join(profiles_dir, filename)
            
            # Delete old profile picture if exists
            if user.profile_picture_url:
                old_filename = os.path.basename(user.profile_picture_url)
                old_filepath = os.path.join(profiles_dir, old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            # Save new file
            with open(filepath, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # Generate full URL
            profile_picture_url = f"http://10.0.2.2:8000/media/profiles/{filename}"
            
            # Update user profile
            user.profile_picture_url = profile_picture_url
            user.save()
            
            return Response({
                "message": "Profile picture updated successfully",
                "profile_picture_url": profile_picture_url,
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "mobile_number": user.mobile_number,
                    "profile_picture_url": user.profile_picture_url,
                    "bio": user.bio,
                    "date_joined": user.date_joined.isoformat()
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to upload profile picture: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteProfilePictureView(APIView):
    """
    API to delete profile picture
    DELETE /api/profile/delete-picture/{user_id}/ - Delete profile picture
    """
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Delete old profile picture if exists
            if user.profile_picture_url:
                profiles_dir = os.path.join(settings.BASE_DIR, 'media', 'profiles')
                old_filename = os.path.basename(user.profile_picture_url)
                old_filepath = os.path.join(profiles_dir, old_filename)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            # Update user profile
            user.profile_picture_url = None
            user.save()
            
            return Response({
                "message": "Profile picture deleted successfully",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "mobile_number": user.mobile_number,
                    "profile_picture_url": None,
                    "bio": user.bio,
                    "date_joined": user.date_joined.isoformat()
                }
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete profile picture: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAccountView(APIView):
    """
    API to delete user account (soft delete)
    DELETE /api/profile/delete-account/{user_id}/ - Delete user account
    """
    parser_classes = [MultiPartParser, FormParser]
    
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            
            # Validate confirmation - check both body and query params
            confirmation = request.data.get('confirmation') or request.query_params.get('confirmation')
            if confirmation != 'DELETE_MY_ACCOUNT':
                return Response(
                    {"error": "Invalid confirmation. Please provide 'DELETE_MY_ACCOUNT' in request body or as query parameter"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Soft delete - deactivate account
            user.is_active = False
            user.email = f"deleted_{user.id}_{user.email}"  # Make email unique
            user.username = f"deleted_{user.id}_{user.username}"  # Make username unique
            user.mobile_number = f"deleted_{user.id}_{user.mobile_number}"  # Make mobile unique
            user.save()
            
            return Response({
                "message": "Account deleted successfully"
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete account: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
