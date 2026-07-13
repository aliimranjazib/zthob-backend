from urllib.parse import urlparse, urlunparse


def media_path_from_url(file_url):
    """Return the relative media path without the /media/ prefix."""
    if not file_url:
        return None

    path = str(file_url)
    if path.startswith(('http://', 'https://')):
        path = urlparse(path).path

    path = path.lstrip('/')
    if path.startswith('media/'):
        path = path[len('media/'):]
    return path or None


def build_public_media_url(request, file_url):
    """
    Build an API media URL that passes through Django/CORS middleware.

    Use this instead of direct /media/ links for browser apps that fetch images
    via XMLHttpRequest (e.g. tailor.mgask.net).
    """
    relative_path = media_path_from_url(file_url)
    if not relative_path:
        return None

    api_path = f'/api/media/{relative_path}'
    if request:
        return request.build_absolute_uri(api_path)

    if str(file_url).startswith(('http://', 'https://')):
        parsed = urlparse(file_url)
        return urlunparse(parsed._replace(path=api_path))

    return api_path
