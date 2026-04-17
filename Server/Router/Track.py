import asyncio
from typing import Union, List, Dict, Any

import aiofiles
import aiohttp
import yandex_music
from fastapi import APIRouter
from postgrest import APIError
from starlette.responses import StreamingResponse
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

@track_router.post("/rating/like/add")
async def like_track_add(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_likes_tracks_add(data.Id)
        return True

    except Exception as e:
        print(e)
        return False


@track_router.post("/rating/dislike/add")
async def dislike_track_add(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_dislikes_tracks_add(data.Id)
        return True

    except Exception as e:
        print(e)
        return False

@track_router.post("/rating/like/remove")
async def like_track_remove(data: Track, user: UserDep) -> bool:
    try:
        client = await get_client_yandex()

        await client.users_likes_tracks_remove(data.Id)
        return True

    except Exception as e:
        print(e)
        return False


@track_router.post("/rating/dislike/remove")
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
    safe_path = Path(f"Data/Track/{track['Name']} - {artist['YID']} - {artist['Name']}.mp3")
    filename = f"{track['Name']} - {artist['Name']}.mp3"

    # Если файл уже есть — отдаём через FileResponse (прогресс будет работать)
    if safe_path.exists():
        return FileResponse(
            path=safe_path,
            media_type="audio/mpeg",
            filename=filename,
            headers={"Content-Disposition": "inline"}
        )

    # Если файла нет — скачиваем из Яндекс.Музыки и сохраняем
    try:
        client = await get_client_yandex()
        yandex_track = (await client.tracks(track["Id"]))[0]  # предполагаем поле YandexId
        download_info = await yandex_track.get_download_info_async(get_direct_links=True)
        direct_link = download_info[0].direct_link

        # Скачиваем и сохраняем файл
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(direct_link) as resp:
                if resp.status != 200:
                    raise HTTPException(404, "Failed to download from Yandex")
                async with aiofiles.open(safe_path, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        await f.write(chunk)

        # После сохранения отдаём через FileResponse (теперь прогресс будет работать)
        return FileResponse(
            path=safe_path,
            media_type="audio/mpeg",
            filename=filename,
            headers={"Content-Disposition": "inline"}
        )

    except Exception as e:
        raise HTTPException(500, f"Yandex download error: {str(e)}")

async def stream_from_url(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async for chunk in resp.content.iter_chunked(8192):
                yield chunk



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
        if direct_url is None:
            print(f"Пропускаем трек {full_track.id} – нет ссылки на скачивание")
            continue

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
    direct_url = None
    og_image = None
    try:
        download_info = await track.get_download_info_async(get_direct_links=True)
        if download_info and len(download_info) > 0:
            direct_url = download_info[0].direct_link
    except Exception as e:
        print(f"Ошибка получения ссылки для трека {track.id}: {e}")
    try:
        og_image = track.get_og_image_url("300x300")
    except Exception as e:
        print(f"Ошибка получения обложки для трека {track.id}: {e}")
    return direct_url, og_image




'''
Сделать: 
2. Передачу радио
'''