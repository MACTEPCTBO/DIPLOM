from fastapi import APIRouter, HTTPException

from Server.Model.Track import Track, Artist
from Server.Router.User import UserDep
from Server.engine import SessionDep
from Player.setting import API, get_client_yandex

track_router = APIRouter(prefix=f"{API}/track", tags=["Track"])


@track_router.get("/{name}")
async def get_track(name: str, session: SessionDep, user: UserDep):
    '''Быстрый поиск по названию'''
    #try:

    track = await session.table("Track").select("*").eq("Name", name).execute()
    if track.data:
        print(track.data)
        new_track = Track(
            Id=track.data[0]['Id'],
            Name=track.data[0]["Name"],
            DurationMs=track.data[0]["Duration_ms"],
            Artists=track.data[0]["Artists"],
            Albums=0,
            URL=track.data[0]["URL"],
            URI=track.data[0]["URI"],
            UserInfo=user.Id
        )
        return new_track
    else:
        client = await get_client_yandex()
        track = (await client.search(name)).tracks.results[0]

        artist = await (session.table("Artist")
                        .select("*")
                        .eq("Name", track.artists[0].name)
                        .eq("YID", track.artists[0].id)
                        .execute())
        if artist.data:
            print(artist)
            new_track = Track(
                    Id=int(track.id),
                    Name=track.title,
                    DurationMs=track.duration_ms,
                    Artists=artist.data[0]['YID'],
                    Albums=0,
                    URL=(await track.get_download_info_async(get_direct_links=True))[0].direct_link,
                    URI=(track.get_og_image_url("50x50")),
                    UserInfo=user.Id
                )
            track = await add_track(
                new_track,
                session
            )
            return new_track
        else:
            print((await track.get_download_info_async(get_direct_links=True)))
            new_track = Track(
                Id=int(track.id),
                Name=track.title,
                DurationMs=track.duration_ms,
                Artists=track.artists[0].id,
                Albums=0,
                URL=(await track.get_download_info_async(get_direct_links=True))[0].direct_link,
                URI=(track.get_og_image_url("50x50")),
                UserInfo=user.Id
            )
            return new_track
    #except Exception as e:
        #print(e)
        #return None



@track_router.post("/")
async def get_track_search(data: Track, session: SessionDep) -> Track | list[Track] | None:
    '''Поиск трека по данным'''
    try:
        srb = session.table("Track").select("*")
        if data.Id is not None:
            srb.eq("Id", data.Id)
        if data.Name is not None:
            srb.eq("Name", data.Name)

    except Exception as e:
        print(e)
        return None


@track_router.post("/search/artist")
async def get_track_artist(data: Track, session: SessionDep) -> Track | list[Track] | None:
    try:
        srb = session.table("Artist").select("*")
        if data.Artists[0].Name is not None:
            srb.eq("Name", data.Artists[0].Name)

        if data.Artists[0].YID is not None:
            srb.eq("YID", data.Artists[0].YID)

        author = await srb.execute()

        srb = session.table("Track").select("*")

        if data.Name:
            track = await srb.eq("Name", data.Name).execute()
        else:
            return HTTPException(status_code=422, detail="Not data in name")


        if track.data:

            return Track(Id=track.data[0].Id, Name=track.data[0].Name, Artists=data.Artists, URL=track.data[0].URL)


    except Exception as e:...




async def add_artist(artist: Artist, session: SessionDep) -> bool:
    try:
        data = {"YID": artist.YID, "Name": artist.Name, "Genres": 0}

        srb = await session.table("Artist").insert(data).execute()
        if srb is not None:
            return True
        else:
            return False

    except Exception as e:
        print(e)
        return False

async def add_track(track: Track, session: SessionDep) -> bool:
    try:
        data = {
            "Name": track.Name,
            "Duration_ms": track.DurationMs,
            "URL": track.URL,
            "URI": track.URI,
            "UserInfo": track.UserInfo,
            "Artists": track.Artists,
            "Albums": track.Albums,
        }

        srb = await session.table("Track").insert(data).execute()
        return True


    except Exception as e:
        print(e)
        return False
