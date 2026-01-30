"""Schemas for Remote DJ agent."""

from pydantic import BaseModel, Field


class PlayRequest(BaseModel):
    """Request to play music."""

    query: str = Field(description="Search query, URI, or playlist/album/track name")
    device_name: str | None = Field(
        default=None,
        description="Target device name (uses active device if not specified)",
    )
    shuffle: bool = Field(default=False, description="Enable shuffle mode")


class DeviceInfo(BaseModel):
    """Spotify device information."""

    id: str
    name: str
    type: str
    is_active: bool
    volume_percent: int | None = None


class PlaybackState(BaseModel):
    """Current playback state."""

    is_playing: bool
    device: DeviceInfo | None = None
    track_name: str | None = None
    artist_name: str | None = None
    album_name: str | None = None
    progress_ms: int | None = None
    duration_ms: int | None = None


class VolumeRequest(BaseModel):
    """Request to set volume."""

    volume_percent: int = Field(ge=0, le=100, description="Volume level 0-100")
    device_name: str | None = Field(default=None, description="Target device")
