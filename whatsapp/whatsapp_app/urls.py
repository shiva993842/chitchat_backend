from django.urls import path
from . import views
from . import group_views
from . import profile_views

urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('register/', views.RegisterView.as_view()),
    path('verify-otp/', views.VerifyOTPView.as_view()),
    path('contacts/', views.FetchContactsView.as_view()),
    path('contacts/add/', views.AddContactView.as_view()),
    path('contacts/delete/', views.DeleteContactView.as_view()),
    path('users/', views.FetchAllUsersView.as_view()),
    path('groups/', views.FetchAllGroupsView.as_view()),
    path('messages/send/', views.SendMessageView.as_view()),
    path('messages/', views.GetMessagesView.as_view()),
    path('messages/unread/', views.GetUnreadMessagesView.as_view()),
    
    # Group Chat APIs
    path('groups/create/', group_views.CreateGroupView.as_view()),
    path('groups/add-members/', group_views.AddGroupMembersView.as_view()),
    path('groups/user/', group_views.GetUserGroupsView.as_view()),
    path('groups/send-message/', group_views.SendGroupMessageView.as_view()),
    path('groups/message/send/', group_views.SendGroupMessageView.as_view()),
    path('groups/messages/', group_views.GetGroupMessagesView.as_view()),
    path('groups/messages/unread/', views.GetUnreadGroupMessagesView.as_view()),
    path('groups/messages/mark-read/', views.MarkGroupMessagesAsReadView.as_view()),
    
    # Profile APIs
    path('profile/<int:user_id>/', profile_views.ViewProfileView.as_view()),
    path('profile/update/<int:user_id>/', profile_views.UpdateProfileView.as_view()),
    path('profile/upload-picture/<int:user_id>/', profile_views.UploadProfilePictureView.as_view()),
    path('profile/delete-picture/<int:user_id>/', profile_views.DeleteProfilePictureView.as_view()),
    path('profile/delete-account/<int:user_id>/', profile_views.DeleteAccountView.as_view()),
]