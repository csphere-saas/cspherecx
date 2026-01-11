from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.views.generic import RedirectView

# Non-i18n patterns (admin, static files, etc.)
urlpatterns = [
    path("admin/", admin.site.urls),
    re_path('grappelli/', include('grappelli.urls')),
    re_path('summernote/', include('django_summernote.urls')),
    path('froala_editor/', include('froala_editor.urls')),
    path('i18n/', include('django.conf.urls.i18n')),  # Keep this outside i18n_patterns for language switching
]

# Static and media files in development
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# i18n patterns (these will have language prefixes like /fr/, /en/, etc.)
urlpatterns += i18n_patterns(
    re_path('rosetta/', include('rosetta.urls')),
    re_path('accounts/', include('allauth.urls')),
    re_path('accounts/', include('django.contrib.auth.urls')),
    re_path('', include('accounts.urls', namespace='accounts')),
    path('login/', RedirectView.as_view(pattern_name='accounts:login'), name='login-redirect'),
    re_path('feedback/', include('feedback.urls', namespace='feedback')),
    re_path('surveys/', include('surveys.urls', namespace='surveys')),
    re_path('cx_analytics/', include('cx_analytics.urls', namespace='cx_analytics')),
    prefix_default_language=True,  # This ensures default language also gets prefix
)