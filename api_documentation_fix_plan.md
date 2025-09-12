# API Documentation Fix Plan

## Current Issues
1. The project has a mixed API documentation setup using both `drf-yasg` and `drf-spectacular`
2. `drf-spectacular` is configured as the default schema class but not installed
3. Imports for `drf_spectacular.views` fail because the package isn't installed

## Analysis
- `drf-yasg` is currently installed and configured with URLs
- `drf-spectacular` is referenced in settings.py as DEFAULT_SCHEMA_CLASS
- There are unused imports for `drf_spectacular.views` in urls.py

## Recommended Solution
Complete the migration to `drf-spectacular` since it's already configured as the default schema class and is a more modern, actively maintained library.

## Steps to Implement

### 1. Add drf-spectacular to Dependencies
- Add `drf-spectacular>=0.27.0` to `pyproject.toml`
- Update `requirements.txt` accordingly

### 2. Update zthob/urls.py
- Remove unused `drf_yasg` imports and configurations
- Properly configure URLs for `drf_spectacular` views
- Use the already imported `drf_spectacular` components

### 3. Clean up settings.py (if needed)
- Ensure `drf_spectacular` is properly configured

## Implementation Details

### Current urls.py Issues
```python
# These imports are not being used:
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# These are the current drf_yasg configurations:
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
       title="Zthob API",
       default_version='v1',
       description="Zthob API documentation",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# Current URLs using drf_yasg:
path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
```

### Proposed urls.py Solution
```python
# Use drf_spectacular imports that are already there:
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# Remove drf_yasg imports and configurations

# Add proper URLs for drf_spectacular:
path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),