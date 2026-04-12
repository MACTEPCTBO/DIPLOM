from fastapi import APIRouter, HTTPException
from pip._internal.network import session

from Server.Model.Track import Track, Artist
from Server.Model.User import User
from Server.Router.User import UserDep
from Server.engine import SessionDep
from setting import API, get_client_yandex
from fastapi import HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import os

track_router = APIRouter(prefix=f"{API}/track", tags=["Track"])






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
async def get_track_artist(data: Track, session: SessionDep, user: User = UserDep) -> Track | list[Track] | None:
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





@track_router.post("/listen")
async def get_track_listen(
        data: Track,
        session: SessionDep,
        user: User = UserDep
):
    try:
        print(data)
        # 1. Получаем информацию о треке из БД (пример)
        track_info = await session.table("Track").select("*").eq("Id", data.Id).execute()
        print(track_info)
        artist = await (session.table("Artist")
                        .select("*")
                        .eq("YID", track_info.data[0]["Artists"])
                        .execute())
        if not track_info:
            raise HTTPException(status_code=404, detail="Track not found")

        # 2. Проверка доступа (например, только для премиум-пользователей)
        #if track_info.is_premium and not user.has_premium:
        #    raise HTTPException(status_code=403, detail="Premium track")

        # 3. Формируем путь к файлу (допустим, файлы хранятся в ./tracks/{track_id}.mp3)
        print("")
        file_path = Path(f"./Data/Track/{track_info["Path"]}.mp3")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio file missing")

        # 5. Возвращаем файл
        print(str(track_info.data[0].title) + " - " + str(track_info.data[0].artists) + " - " + str(track_info.data[0].artists))

        return FileResponse(
            path=file_path,
            media_type="audio/mpeg",  # или audio/ogg, audio/flac и т.д.
            filename=f"{str(track_info.data[0]["title"]) + " - " + str(artist.data[0]["YID"]) + " - " + str(artist.data[0]["name"]) }.mp3",  # имя для сохранения
            headers={"Content-Disposition": "inline"}  # воспроизводить в браузере
        )

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error")


@track_router.get("/{name}")
async def get_track(name: str, session: SessionDep, user: UserDep):
    '''Быстрый поиск по названию'''
    #try:

    track = await session.table("Track").select("*").eq("Name", name).execute()
    if track.data:
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
        track_ = (await client.search(name)).tracks.results[0]

        artist = await (session.table("Artist")
                        .select("*")
                        .eq("Name", track_.artists[0].name)
                        .eq("YID", track_.artists[0].id)
                        .execute())
        if artist.data:
            new_track = Track(
                    Id=int(track_.id),
                    Name=track_.title,
                    DurationMs=track_.duration_ms,
                    Artists=artist.data[0]['YID'],
                    Albums=0,
                    URL=(await track_.get_download_info_async(get_direct_links=True))[0].direct_link,
                    URI=(track_.get_og_image_url("50x50")),
                    UserInfo=user.Id,
                    Path="Data/Track/" + str(track_.title) + " - " + str(track_.artists[0].id) + " - " + str(track_.artists[0].name),
                )
            track = await add_track(
                new_track,
                session
            )
            return new_track
        else:
            new_track = Track(
                Id=int(track_.id),
                Name=track_.title,
                DurationMs=track_.duration_ms,
                Artists=track_.artists[0].id,
                Albums=0,
                URL=(await track_.get_download_info_async(get_direct_links=True))[0].direct_link,
                URI=(track_.get_og_image_url("50x50")),
                UserInfo=user.Id,
                Path="Data/Track/" + str(track_.title) + " - " + str(track_.artists[0].id) + " - " + str(track_.artists[0].name)
            )

            response = await session.rpc(
                "add_artist_and_track",
                {
                    "p_artist_yid": track_.artists[0].id,
                    "p_artist_name": track_.artists[0].name,
                    "p_track_name": track_.title,
                    "p_duration_ms": track_.duration_ms,
                    "p_url": (await track_.get_download_info_async(get_direct_links=True))[0].direct_link,
                    "p_uri": track_.get_og_image_url("50x50"),
                    "p_user_info": user.Id,
                    "p_album_name": 0
                }
            ).execute()
            print(response)

            await track_.download_async(
                filename="Data/Track/" + str(track_.title) + " - " + str(track_.artists[0].id) + " - " + str(
                    track_.artists[0].name))

            return new_track
    #except Exception as e:
        #print(e)
        #return None




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
