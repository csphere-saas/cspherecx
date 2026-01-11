from django.conf import settings

def survey_settings(request):
    return {
        'SURVEY_SETTINGS': {
            'MAX_RESPONSE_LENGTH': getattr(settings, 'MAX_RESPONSE_LENGTH', 1000),
            'DEFAULT_LANGUAGE': getattr(settings, 'DEFAULT_LANGUAGE', 'en'),
        }
    }