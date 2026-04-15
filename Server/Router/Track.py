import asyncio
from typing import Union, List, Dict, Any

import yandex_music
from fastapi import APIRouter
from postgrest import APIError
from supabase import AsyncClient
from yandex_music import ClientAsync

from Server.Model.Track import Track, Playlist, Artist
from Server.Router.User import UserDep
from Server.engine import SessionDep, get_supabase_client
from setting import API, get_client_yandex
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

track_router = APIRouter(prefix=f"{API}/track", tags=["Track"])

@track_router.get("/rating/like/add")
async def like_track_add(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_likes_tracks_add(data.Id)
        return True

    except Exception as e:
        print(e)
        return False


@track_router.get("/rating/dislike/add")
async def dislike_track_add(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_dislikes_tracks_add(data.Id)
        return True

    except Exception as e:
        print(e)
        return False

@track_router.get("/rating/like/remove")
async def like_track_remove(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_likes_tracks_remove(data.Id)
        return True

    except Exception as e:
        print(e)
        return False


@track_router.get("/rating/dislike/remove")
async def dislike_track_remove(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_dislikes_tracks_remove(data.Id)
        return True

    except Exception as e:
        print(e)
        return False

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
async def get_track(name: str, session: SessionDep, user: UserDep) -> Track:
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

@track_router.get("/playlist/likes/{token}")
async def get_likes_playlist(token: str, session: SessionDep, user: UserDep) -> Playlist:
    try:
        client = await get_client_yandex()

        playlist = Playlist(Id=0, Name="Понравившееся", Count=0, Tracks=[])
        tracks = []

        liked_tracks = (await client.users_likes_tracks()).tracks
        track_ids = [track.id for track in liked_tracks]
        print(track_ids)

        # предположим, есть метод client.tracks_by_ids (или что-то подобное)
        tracks_data = await client.tracks(track_ids)  # возвращает список треков по порядку
        tracks = []
        for track_data in tracks_data:
            print(track_data)
            tracks.append(await get_track(track_data.title, session, user))

        playlist.Count = len(tracks)
        playlist.Tracks = tracks

        return playlist

    except Exception as e:
        print(e)
        return Playlist(Id=0, Name="Ошибка", Count=0, Tracks=[])



@track_router.get('/playlist/likes/{token}/all')
async def create_likes_playlist(
        token: str,
        user_info_id: UserDep,
        playlist_name: str = "Liked Songs",
        batch_size: int = 50,
        max_concurrent_downloads: int = 10
) -> Playlist:
    """
    Извлекает все понравившиеся треки пользователя из Яндекс.Музыки,
    сохраняет их в Supabase и возвращает объект плейлиста.
    """
    yandex_client: ClientAsync = await get_client_yandex()
    supabase: AsyncClient = await get_supabase_client()

    # 1. Получение всех понравившихся треков
    liked_tracks = await yandex_client.users_likes_tracks()
    if not liked_tracks:
        return Playlist(Id=0, Name=playlist_name, Tracks=[], Count=0)

    # Отбираем только валидные треки
    valid_tracks = [track for track in liked_tracks if track and track.id]
    if not valid_tracks:
        return Playlist(Id=0, Name=playlist_name, Tracks=[], Count=0)

    # 2. Параллельное получение полных данных о треках (базовая информация)
    track_ids = [t.id for t in valid_tracks]
    chunk_tasks = []
    for i in range(0, len(track_ids), batch_size):
        chunk = track_ids[i:i + batch_size]
        chunk_tasks.append(yandex_client.tracks(chunk))

    chunk_results = await asyncio.gather(*chunk_tasks)

    # Собираем полные объекты треков
    full_tracks: List[yandex_music.Track] = []
    for chunk in chunk_results:
        if chunk:
            full_tracks.extend([t for t in chunk if t])

    # 3. Параллельное получение прямых ссылок и обложек с семафором для ограничения конкурентности
    semaphore = asyncio.Semaphore(max_concurrent_downloads)

    async def fetch_with_limit(track: yandex_music.Track):
        async with semaphore:
            return await fetch_track_url_and_uri(track)

    url_uri_tasks = [fetch_with_limit(track) for track in full_tracks]
    url_uri_results = await asyncio.gather(*url_uri_tasks)

    # 4. Формирование объектов Track и записей для БД
    track_objects: List[Track] = []
    supabase_records: List[Dict[str, Any]] = []

    for full_track, (direct_url, og_uri) in zip(full_tracks, url_uri_results):
        artist_id = full_track.artists[0].id if full_track.artists else None
        album_id = full_track.albums[0].id if full_track.albums else None

        # Объект для внутреннего использования
        track_obj = Track(
            Id=int(full_track.id),
            Name=full_track.title,
            DurationMs=full_track.duration_ms,
            Artists=artist_id,
            Albums=0,
            URL=direct_url,
            URI=og_uri,
            UserInfo=user_info_id.Id,
            Path=None
        )
        track_objects.append(track_obj)

        # Словарь для вставки в Supabase с корректными именами колонок
        supabase_records.append({
            "Id": int(full_track.id),
            "Name": full_track.title,
            "Duration_ms": full_track.duration_ms,
            "Artist": artist_id,
            "Albums": 0,
            "URL": direct_url,
            "URI": og_uri,
            "UserInfo": user_info_id.Id,
            "Path": None
        })

    # 5. Параллельная вставка в Supabase
    if supabase_records:
        insert_tasks = []
        for i in range(0, len(supabase_records), batch_size):
            batch = supabase_records[i:i + batch_size]
            insert_tasks.append(
                supabase.table("Track").upsert(batch, on_conflict="Id").execute()
            )
        await asyncio.gather(*insert_tasks)

    # 6. Возврат плейлиста

    return Playlist(
        Id=hash(f"{user_info_id.Id}"),
        Name=playlist_name,
        Tracks=track_objects,
        Count=len(track_objects)
    )

@track_router.get("/playlist/{name}/{token}")
async def get_playlist(name: str, token: str, session: SessionDep, user: UserDep) -> Playlist:
    try:
        client = await get_client_yandex()


        playlists = await client.users_playlists_list()
        for playlist in playlists:
            if playlist.title == name:
                playlist_ = await client.users_playlists(kind=playlists[0].kind)
                result_playlist = Playlist(Id=int(playlist_.kind), Name=name, Count=int(playlist_.track_count), Tracks=[])
                break
        else:
            return Playlist(Id=0, Name='Плейлист не найден', Count=0, Tracks=[])

        tracks = []
        for track in playlist_.tracks:
            tracks.append(await get_track(track.track.title, session, user))

        result_playlist.Tracks = tracks


        return result_playlist


    except Exception as e:
        print(e)
        return e





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

async def is_artists(tracks, session: SessionDep) -> Artist:

    # 1. Собираем уникальных артистов (по YID) из всех треков
    unique_artists = {}
    for track in tracks:
        if not track.artists:
            continue
        artist = track.artists[0]
        if artist.id not in unique_artists:
            unique_artists[artist.id] = artist.name

    if not unique_artists:
        return []

    # 2. Один запрос: получаем уже существующих артистов
    existing = await session.table("Artist") \
        .select("*") \
        .in_("YID", list(unique_artists.keys())) \
        .execute()

    existing_map = {row["YID"]: row for row in existing.data}

    # 3. Определяем, каких артистов нужно добавить
    new_artists = []
    for yid, name in unique_artists.items():
        if yid not in existing_map:
            new_artists.append({"YID": yid, "Name": name})

    # 4. Массовая вставка новых артистов
    if new_artists:
        inserted = await session.table("Artist") \
            .insert(new_artists) \
            .execute()
        # Добавляем вставленных в общий словарь
        for row in inserted.data:
            existing_map[row["YID"]] = row

    # 5. Формируем результат в порядке исходных треков
    artists = []
    for track in tracks:
        if track.artists:
            yid = track.artists[0].id
            artists.append(existing_map[yid])
        else:
            artists.append(None)  # или пропустить, как в оригинале?

    return artists

async def fetch_track_url_and_uri(track: yandex_music.Track) -> tuple[str | None, str | None]:
    """Параллельно получает прямую ссылку на скачивание и URI обложки."""
    try:
        # Задачи на получение ссылок
        url_task = asyncio.create_task(track.get_download_info_async(get_direct_links=True))
        download_info = await url_task

        uri_task = track.get_og_image_url("300x300")
        og_image = uri_task


        direct_url = download_info[0].direct_link if download_info else None
        return direct_url, og_image
    except Exception as e:
        # В случае ошибки возвращаем None для проблемного поля
        print(f"Ошибка получения ссылок для трека {track.id}: {e}")
        return None, None




'''
Сделать: 
2. Передачу радио
'''