from fastapi import APIRouter, HTTPException
from pip._internal.network import session
from postgrest import APIError

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





@track_router.get("/listen/{Id}")
async def get_track_listen(Id: int, session: SessionDep):
    # 1. Получаем трек
    track_result = await session.table("Track").select("*").eq("Id", Id).execute()
    if not track_result.data:
        raise HTTPException(status_code=404, detail="Track not found")
    track = track_result.data[0]  # словарь

    # 2. Получаем исполнителя
    artist_result = await session.table("Artist").select("*").eq("YID", track["Artist"]).execute()
    if not artist_result.data:
        raise HTTPException(status_code=404, detail="Artist not found")
    artist = artist_result.data[0]

    # 3. Проверка доступа (если нужно)
    # if track.get("is_premium") and not user.has_premium:
    #     raise HTTPException(status_code=403, detail="Premium track")

    # 4. Формируем безопасный путь к файлу
    safe_path = Path(track["Path"] + ".mp3")
    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing")

    # 5. Имя для скачивания
    filename = f"{track['Name']} - {artist['Name']}.mp3"

    return FileResponse(
        path=safe_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={"Content-Disposition": "inline"}
    )

@track_router.get("/{name}")
async def get_track(name: str, session: SessionDep, user: UserDep):
    '''Быстрый поиск по названию'''
    # 1. Проверка в БД на наличие трека
    client = await get_client_yandex()

    record = (await session.table("Track").select("*").ilike("Name", f'%{name}%').execute()).data

    if len(record):
        # Возвращение найденной записи
        return await create_track_in_bd(**record[0])
    else:
        # 2. Создаём и возвращаем найденную запись

        track = (await client.search(name)).tracks.results[0]
        artist = (await session.table("Artist").select("*").eq("YID", track.artists[0].id).execute()).data

        if len(artist):
            # Создаём запись и возвращаем её

            new_track = await create_track(session, Id=int(track.id),
                                           Name=track.title,
                                           DurationMs=track.duration_ms,
                                           Artists=artist[0]['YID'],
                                           Albums=0,
                                           URL=(await track.get_download_info_async(get_direct_links=True))[
                                               0].direct_link,
                                           URI=(track.get_og_image_url("300x300")),
                                           UserInfo=user.Id,
                                           Path="Data/Track/" + str(track.title) + " - " + str(
                                               track.artists[0].id) + " - " + str(
                                               track.artists[0].name), )

            await track.download_async(filename="Data/Track/" + str(track.title) + " - " + str(
                track.artists[0].id) + " - " + str(
                track.artists[0].name) + ".mp3")
            return new_track
        else:
            # 3. Добавляем автора и после создаём запись и возвращаем её
            try:
                new_artist = (await session.table("Artist").insert(
                    {"YID": track.artists[0].id, "Name": track.artists[0].name}).execute())


                new_track = await create_track(session, Id=int(track.id),
                                           Name=track.title,
                                           DurationMs=track.duration_ms,
                                           Artists=new_artist.data[0]['YID'],
                                           Albums=0,
                                           URL=(await track.get_download_info_async(get_direct_links=True))[
                                               0].direct_link,
                                           URI=(track.get_og_image_url("300x300")),
                                           UserInfo=user.Id,
                                           Path="Data/Track/" + str(track.title) + " - " + str(
                                               track.artists[0].id) + " - " + str(
                                               track.artists[0].name), )

                await track.download_async(filename="Data/Track/" + str(track.title) + " - " + str(
                    track.artists[0].id) + " - " + str(
                    track.artists[0].name) + ".mp3")

                return new_track

            except APIError as e:
                print(e)
                return Track()



            return new_track




async def create_track(session: SessionDep = None, **kwargs) -> Track:
    """Создаёт трек для отправления пользователю.
        Так же отправляет запись в БД"""
    try:
        data = {
            "Id": kwargs["Id"],
            "Name": kwargs['Name'],
            "Duration_ms": kwargs['DurationMs'],
            "URL": kwargs['URL'],
            "URI": kwargs['URI'],
            "UserInfo": kwargs['UserInfo'],
            "Albums": kwargs['Albums'],
            "Path": kwargs['Path'],
            'Artist': kwargs['Artists'],
        }
        if session:
            data = await session.table('Track').insert(data).execute()

        return Track(**kwargs)
    except Exception as e:
        print(e)
        return Track()

async def create_track_in_bd(**kwargs) -> Track:
    kwargs['DurationMs'] = kwargs['Duration_ms']
    kwargs['Artists'] = kwargs['Artist']
    return await create_track(**kwargs)


