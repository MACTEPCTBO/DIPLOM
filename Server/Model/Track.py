from datetime import datetime
from typing import Union

from Server.Model.Base import Base


class Artist(Base):
    Id: int | None = None
    YID: int | None = None
    Name: str | None = None


class Album(Base):
    Id: int
    Name: str
    CountTracks: int
    Artists: list[Artist] | None
    Description: str | None



class Track(Base):
    Id: int | Union[int] | None = None
    Name: str | None = None
    DurationMs: int | None = None
    Artists: int | None = None
    Albums: int | None = None
    URL: str | None = None
    URI: str | None = None
    UserInfo: int | None = None
    Path: str | None = None


class Playlist(Base):
    Id: int
    Name: str
    Tracks: list[Track] | None
    Count: int = 0


class RadioStart(Base):
    Station: str
    Queue: str | int | None = None

class RadioResponse(Base):
    Tracks: list[Track]
    BatchId: str


class FeedBack(Base):
    Station: str
    Type_: str
    Timestamp: int
    From_: str
    BatchId: str | None
    TotalPlayedSeconds: float
    TrackId: int