"""Remote DJ agent - Spotify controller using SpotAPI (unofficial)."""

import json
import logging
from pathlib import Path
from typing import Any

from pandaemon.agents.base import BaseAgent
from pandaemon.agents.remote_dj.schemas import DeviceInfo, PlaybackState, PlayRequest
from pandaemon.config import get_settings
from pandaemon.kernel.schemas import AgentResponse

logger = logging.getLogger(__name__)


class RemoteDJAgent(BaseAgent):
    """
    Remote DJ Agent - Spotify controller using SpotAPI.
    
    Uses SpotAPI (unofficial) to control Spotify via browser session cookies.
    No developer app required - authenticates using your Spotify account cookies.
    
    Setup:
    1. Go to https://open.spotify.com and log in
    2. Export cookies using browser extension (JSON format)
    3. Save to data/spotify_cookies.json
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._login = None
        self._player = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "remote_dj"

    @property
    def description(self) -> str:
        return "Spotify remote control - play music, control volume, manage devices (uses SpotAPI)"

    def get_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for Remote DJ."""
        return [
            {
                "name": "play",
                "description": "Search for and play music (track, album, playlist, or artist)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query or Spotify URI",
                        },
                        "shuffle": {
                            "type": "boolean",
                            "description": "Enable shuffle",
                            "default": False,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "pause",
                "description": "Pause current playback",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "resume",
                "description": "Resume paused playback",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "next",
                "description": "Skip to next track",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "previous",
                "description": "Go to previous track",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "set_volume",
                "description": "Set playback volume",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "volume_percent": {
                            "type": "integer",
                            "description": "Volume 0-100",
                            "minimum": 0,
                            "maximum": 100,
                        },
                    },
                    "required": ["volume_percent"],
                },
            },
            {
                "name": "get_playback",
                "description": "Get current playback state",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "search",
                "description": "Search for music without playing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
        ]

    async def execute(self, action: str, parameters: dict[str, Any]) -> AgentResponse:
        """Execute a Remote DJ action."""
        # Ensure initialized
        if not self._initialized:
            init_result = await self._initialize()
            if not init_result:
                return AgentResponse(
                    status="error",
                    error="Spotify not configured. Export cookies from open.spotify.com to data/spotify_cookies.json",
                )

        if action == "play":
            return await self._play(parameters)
        elif action == "pause":
            return await self._pause()
        elif action == "resume":
            return await self._resume()
        elif action == "next":
            return await self._next_track()
        elif action == "previous":
            return await self._previous_track()
        elif action == "set_volume":
            return await self._set_volume(parameters)
        elif action == "get_playback":
            return await self._get_playback()
        elif action == "search":
            return await self._search(parameters)
        else:
            return AgentResponse(status="error", error=f"Unknown action: {action}")

    async def _initialize(self) -> bool:
        """Initialize SpotAPI client using cookies."""
        try:
            from spotapi import Login, Song, Config, NoopLogger
            from spotapi.types.saver import JSONSaver

            cookies_path = self._settings.spotify_cookies_path

            # Check if cookies file exists
            if cookies_path.exists():
                # Load from saved session
                try:
                    saver = JSONSaver(str(cookies_path.parent))
                    self._login = Login.from_saver(saver)
                    logger.info("Loaded Spotify session from cookies")
                except Exception as e:
                    logger.warning(f"Failed to load saved session: {e}")
                    # Try to login with credentials
                    if self._settings.spotify_email and self._settings.spotify_password:
                        return await self._login_with_credentials()
                    return False
            elif self._settings.spotify_email and self._settings.spotify_password:
                # Login with credentials
                return await self._login_with_credentials()
            else:
                logger.warning("No Spotify cookies or credentials configured")
                return False

            self._initialized = True
            return True

        except ImportError:
            logger.error("spotapi not installed. Run: pip install spotapi")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize SpotAPI: {e}")
            return False

    async def _login_with_credentials(self) -> bool:
        """Login using email/password (requires CAPTCHA solver or manual verification)."""
        try:
            from spotapi import Login, Config, NoopLogger
            from spotapi.types.saver import JSONSaver

            # Note: This method may require a CAPTCHA solver for first login
            # For now, we'll just inform the user to use cookies instead
            logger.warning(
                "SpotAPI login with credentials requires CAPTCHA solving. "
                "Please export cookies from open.spotify.com instead."
            )
            return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def _play(self, params: dict[str, Any]) -> AgentResponse:
        """Play music based on query."""
        try:
            request = PlayRequest(**params)
        except Exception as e:
            return AgentResponse(status="error", error=f"Invalid parameters: {e}")

        try:
            from spotapi import Song

            song = Song()

            # Check if query is a Spotify URI
            if request.query.startswith("spotify:"):
                uri = request.query
            else:
                # Search for content
                results = song.query_songs(request.query, limit=1)
                items = results.get("data", {}).get("searchV2", {}).get("tracksV2", {}).get("items", [])
                
                if not items:
                    return AgentResponse(
                        status="error",
                        error=f"No results found for: {request.query}",
                    )
                
                # Get first track URI
                track = items[0].get("item", {}).get("data", {})
                uri = track.get("uri", "")
                track_name = track.get("name", "Unknown")
                artist_name = track.get("artists", {}).get("items", [{}])[0].get("profile", {}).get("name", "Unknown")

            # Note: SpotAPI public API doesn't directly control playback
            # Playback control requires authenticated session
            if self._login:
                # Use Player API if we have login session
                from spotapi import Player
                player = Player(self._login)
                player.play(uri)
                
                return AgentResponse(
                    status="success",
                    response=f"Playing: {track_name} by {artist_name}",
                    data={"uri": uri, "track": track_name, "artist": artist_name},
                )
            else:
                # Return search result without playback
                return AgentResponse(
                    status="success",
                    response=f"Found: {track_name} by {artist_name}. Open in Spotify: {uri}",
                    data={"uri": uri, "track": track_name, "artist": artist_name},
                )

        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _search(self, params: dict[str, Any]) -> AgentResponse:
        """Search for music."""
        query = params.get("query", "")
        limit = params.get("limit", 5)

        if not query:
            return AgentResponse(status="error", error="Query required")

        try:
            from spotapi import Song

            song = Song()
            results = song.query_songs(query, limit=limit)
            items = results.get("data", {}).get("searchV2", {}).get("tracksV2", {}).get("items", [])

            tracks = []
            for item in items:
                track_data = item.get("item", {}).get("data", {})
                tracks.append({
                    "name": track_data.get("name", "Unknown"),
                    "artist": track_data.get("artists", {}).get("items", [{}])[0].get("profile", {}).get("name", "Unknown"),
                    "uri": track_data.get("uri", ""),
                })

            if not tracks:
                return AgentResponse(
                    status="success",
                    response=f"No results for: {query}",
                    data={"tracks": []},
                )

            track_list = ", ".join([f"{t['name']} by {t['artist']}" for t in tracks[:3]])
            return AgentResponse(
                status="success",
                response=f"Found: {track_list}",
                data={"tracks": tracks},
            )

        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _pause(self) -> AgentResponse:
        """Pause playback."""
        if not self._login:
            return AgentResponse(status="error", error="Playback control requires authenticated session")

        try:
            from spotapi import Player
            player = Player(self._login)
            player.pause()
            return AgentResponse(status="success", response="Playback paused")
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _resume(self) -> AgentResponse:
        """Resume playback."""
        if not self._login:
            return AgentResponse(status="error", error="Playback control requires authenticated session")

        try:
            from spotapi import Player
            player = Player(self._login)
            player.resume()
            return AgentResponse(status="success", response="Playback resumed")
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _next_track(self) -> AgentResponse:
        """Skip to next track."""
        if not self._login:
            return AgentResponse(status="error", error="Playback control requires authenticated session")

        try:
            from spotapi import Player
            player = Player(self._login)
            player.next()
            return AgentResponse(status="success", response="Skipped to next track")
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _previous_track(self) -> AgentResponse:
        """Go to previous track."""
        if not self._login:
            return AgentResponse(status="error", error="Playback control requires authenticated session")

        try:
            from spotapi import Player
            player = Player(self._login)
            player.previous()
            return AgentResponse(status="success", response="Went to previous track")
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _set_volume(self, params: dict[str, Any]) -> AgentResponse:
        """Set playback volume."""
        if not self._login:
            return AgentResponse(status="error", error="Volume control requires authenticated session")

        volume = params.get("volume_percent", 50)
        volume = max(0, min(100, volume))

        try:
            from spotapi import Player
            player = Player(self._login)
            player.set_volume(volume)
            return AgentResponse(
                status="success",
                response=f"Volume set to {volume}%",
            )
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    async def _get_playback(self) -> AgentResponse:
        """Get current playback state."""
        if not self._login:
            return AgentResponse(
                status="success",
                response="Playback info requires authenticated session. Search is available.",
                data={"is_playing": False},
            )

        try:
            from spotapi import Player
            player = Player(self._login)
            state = player.get_state()

            if not state:
                return AgentResponse(
                    status="success",
                    response="No active playback",
                    data={"is_playing": False},
                )

            return AgentResponse(
                status="success",
                response=f"Now playing: {state.get('track', 'Unknown')}",
                data=state,
            )
        except Exception as e:
            return AgentResponse(status="error", error=str(e))
