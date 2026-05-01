"""
Utility functions for the application
"""


def format_duration(duration_ms):
    """Format duration from milliseconds to MM:SS"""
    seconds = int(duration_ms / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"


def validate_range(offset, limit, total):
    """Validate and adjust range parameters"""
    error = None
    
    if offset < 0:
        offset = 0
        error = "Offset ajustado a 0"
    elif offset >= total:
        error = f"Offset ({offset}) excede tamaño ({total})"
        return 0, 0, error
    
    if limit <= 0:
        error = "Limite debe ser > 0"
        return offset, 0, error
    
    available = total - offset
    if limit > available:
        limit = available
        error = f"Limite ajustado a {limit}"
    
    if limit > 100:
        limit = 100
        error = "Limite ajustado a 100"
    
    return offset, limit, error


def validate_credentials(spotify_client_id, spotify_client_secret):
    """Validate that Spotify credentials are provided (YouTube no longer needed)"""
    errors = []
    
    if not spotify_client_id or not spotify_client_id.strip():
        errors.append("Spotify Client ID requerido")
    
    if not spotify_client_secret or not spotify_client_secret.strip():
        errors.append("Spotify Client Secret requerido")
    
    return errors
