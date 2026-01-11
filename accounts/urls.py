from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *
from . import views
from .views import HomePageView
from .org_views import *
from .customer_views import *
from .product_views import *

app_name = 'accounts'

urlpatterns = [
    #path('', views.home_page, name="home-page"),
    path('', HomePageView.as_view(), name="home-page"),
    # Registration
    path('register/', views.RegisterView.as_view(), name='register'),
     
    # Login & Logout
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Allauth URLs (for social login)
    path('social/', include('allauth.urls')),

    # Password Reset Flow
    path('password-reset/', CustomPasswordResetView.as_view(), name='password-reset'),

    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password-reset-done'),
    path('password-reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(),name='password_reset_confirm'),
    path('password-reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password-reset-complete'),
    
    # Password Change (for authenticated users)
    path('password-change/', CustomPasswordChangeView.as_view(), name='password-change'),
    path('password-change/done/', PasswordChangeDoneView.as_view(), name='password-change-done'),
    
    # User Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/edit/', ProfileUpdateView.as_view(), name='profile-update'),

    # Email Change
    path('email-change/', EmailChangeView.as_view(), name='email-change'),
    
    # Account Deletion
    path('account/delete/', AccountDeletionView.as_view(), name='account-delete'),
    path('account/deleted/', AccountDeletedView.as_view(), name='account-deleted'),
    
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    ##### Site files #####
    path("aboutus/", aboutus, name="about"),
    path("privacy/", privacy, name="privacy"),
    path("terms/", conditions, name="terms"),
    path("contact/", contact, name="contact"),
    path("services/", services, name="services"),
    path("packages/", compliance, name="compliance"),
    path("careers/", careers, name="careers"),
    path("help/", help, name="help"),
    path("doc/", doc, name="docs"),
    path("api-docs/", api_docs, name="api-docs"),
    path("status/", status, name="status"),
    
    ###########Organization URLs#############
    path('organizations/', OrganizationListView.as_view(), name='org-list'),
    path('my-organizations/', OrganizationUserListView.as_view(), name='org-list-user'),
    path('organizations/create/', OrganizationCreateView.as_view(), name='org-create'),
    path('organizations/<uuid:pk>/', OrganizationDetailView.as_view(), name='org-detail'),
    path('organizations/<uuid:pk>/edit/', OrganizationUpdateView.as_view(), name='org-update'),
    path('organizations/<uuid:pk>/delete/', OrganizationDeleteView.as_view(), name='org-delete'),
    path('organizations/<uuid:pk>/settings/', OrganizationSettingsView.as_view(), name='org-settings'),
    
    # Member management
    path('organizations/<uuid:pk>/members/', OrganizationMemberListView.as_view(), name='org-member-list'),
    path('organizations/<uuid:pk>/members/add/', OrganizationMemberCreateView.as_view(), name='org-member-add'),
    #path('organizations/<uuid:pk>/members/<uuid:pk>/edit/', OrganizationMemberUpdateView.as_view(), name='org-member-edit'),
    path('organizations/<uuid:org_pk>/members/<uuid:member_pk>/edit/', OrganizationMemberUpdateView.as_view(), name='org-member-edit'),
    #path('organizations/<uuid:pk>/members/<uuid:pk>/delete/', OrganizationMemberDeleteView.as_view(), name='org-member-delete'),
    path('organizations/<uuid:org_pk>/members/<uuid:member_pk>/delete/', OrganizationMemberDeleteView.as_view(), name='org-member-delete'),
    path('organizations/<uuid:pk>/members/invite/', OrganizationMemberInviteView.as_view(), name='org-member-invite'),
    path('invitations/accept/<str:token>/', AcceptInvitationView.as_view(), name='accept-invitation'),
    #path('organizations/<uuid:pk>/members/<uuid:pk>/', OrganizationMemberDetailView.as_view(), name='org-member-detail'),
    path('organizations/<uuid:org_pk>/members/<uuid:member_pk>/', OrganizationMemberDetailView.as_view(), name='org-member-detail'),
    #path('organizations/<uuid:pk>/members/<uuid:pk>/deactivate/', OrganizationMemberDeactivateView.as_view(), name='org-member-deactivate'),
    path('organizations/<uuid:org_pk>/members/<uuid:member_pk>/deactivate/', OrganizationMemberDeactivateView.as_view(), name='org-member-deactivate'),
    #path('organizations/<uuid:pk>/members/<uuid:pk>/reactivate/', OrganizationMemberReactivateView.as_view(), name='org-member-reactivate'),
    path('organizations/<uuid:org_pk>/members/<uuid:member_pk>/reactivate/', OrganizationMemberReactivateView.as_view(), name='org-member-reactivate'),
     path('organizations/<uuid:pk>/transfer-ownership/', OrganizationTransferOwnershipView.as_view(), name='org-transfer-ownership'),
    
    ########### Products URLs#############
    path('organizations/<uuid:organization_pk>/products/', ProductListView.as_view(), name='product-list'),
    path('organizations/<uuid:organization_pk>/products/create/', ProductCreateView.as_view(), name='product-create'),
    
    path('organizations/<uuid:organization_pk>/products/<uuid:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('organizations/<uuid:organization_pk>/products/<uuid:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('organizations/<uuid:organization_pk>/products/<uuid:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
    
    ########### Customers URLs#############
    path('organizations/<uuid:organization_pk>/customers/', CustomerListView.as_view(), name='customer-list'),
    #path('organizations/<uuid:organization_pk>/customers/create/', CustomerCreateView.as_view(), name='customer-create'),
    path(
        'organizations/<uuid:organization_id>/customers/create/',
        CustomerCreateView.as_view(),
        name='customer-create'
    ),
    path('organizations/<uuid:organization_pk>/customers/<uuid:pk>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('organizations/<uuid:organization_pk>/customers/<uuid:pk>/update/', CustomerUpdateView.as_view(), name='customer-update'),
    path('organizations/<uuid:organization_pk>/customers/<uuid:pk>/delete/', CustomerDeleteView.as_view(), name='customer-delete'),
    
]