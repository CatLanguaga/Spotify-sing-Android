"""
YouTube search client using pytubefix (no API key required)
"""
from pytubefix import Search


class YouTubeClient:
    def __init__(self):
        """Initialize YouTube client - no API key needed with pytubefix"""
        pass
    
    def search_song(self, song_name, artist, duration_ms, max_results=10):
        """
        Search for a song on YouTube matching name, artist, and duration
        
        Args:
            song_name: Name of the song
            artist: Artist name
            duration_ms: Expected duration in milliseconds
            max_results: Maximum results to check
            
        Returns:
            YouTube video URL if found, None otherwise
        """
        try:
            # Create search query
            query = f"{song_name} {artist}"
            
            # Search using pytubefix
            search = Search(query)
            
            # Get results
            results = search.videos[:max_results] if search.videos else []
            
            if not results:
                return None
            
            # Convert expected duration to seconds
            expected_duration_sec = duration_ms / 1000
            tolerance_sec = 20  # ±20 seconds
            
            # Find best match by duration
            for video in results:
                try:
                    video_duration_sec = video.length  # Duration in seconds
                    
                    if video_duration_sec is None:
                        continue
                    
                    duration_diff = abs(video_duration_sec - expected_duration_sec)
                    
                    if duration_diff <= tolerance_sec:
                        return f"https://www.youtube.com/watch?v={video.video_id}"
                        
                except Exception as e:
                    print(f"Error checking video: {e}")
                    continue
            
            # If no exact match, return first result as fallback
            if results:
                return f"https://www.youtube.com/watch?v={results[0].video_id}"
            
            return None
            
        except Exception as e:
            print(f"YouTube search error: {e}")
            return None
    
    def get_video_info(self, video_url):
        """Get video information"""
        try:
            from pytubefix import YouTube
            
            yt = YouTube(video_url)
            return {
                'title': yt.title,
                'author': yt.author,
                'length_seconds': yt.length
            }
        except Exception:
            return None
