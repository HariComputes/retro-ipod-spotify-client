import spotipy
import datastore
from spotipy.oauth2 import SpotifyOAuth
import threading
import time
import json

class UserDevice():
    __slots__ = ['id', 'name', 'is_active']
    def __init__(self, id, name, is_active):
        self.id = id
        self.name = name
        self.is_active = is_active

class UserTrack():
    __slots__ = ['title', 'artist', 'album', 'uri']
    def __init__(self, title, artist, album, uri):
        self.title = title
        self.artist = artist
        self.album = album
        self.uri = uri

    def __str__(self):
        return self.title + " - " + self.artist + " - " + self.album

class UserAlbum():
    __slots__ = ['name', 'artist', 'track_count', 'uri']
    def __init__(self, name, artist, track_count, uri):
        self.name = name
        self.artist = artist
        self.uri = uri
        self.track_count = track_count

    def __str__(self):
        return self.name + " - " + self.artist

class UserEpisode():
    __slots__ = ['name', 'publisher', 'show', 'uri']
    def __init__(self, name, publisher, show, uri):
        self.name = name
        self.publisher = publisher
        self.show = show
        self.uri = uri

    def __str__(self):
        return self.name + " - " + self.publisher

class UserShow():
    __slots__ = ['name', 'publisher', 'episode_count', 'uri']
    def __init__(self, name, publisher, episode_count, uri):
        self.name = name
        self.publisher = publisher
        self.episode_count = episode_count
        self.uri = uri

    def __str__(self):
        return self.name + " - " + self.publisher

class UserArtist():
    __slots__ = ['name', 'uri']
    def __init__(self, name, uri):
        self.name = name
        self.uri = uri

    def __str__(self):
        return self.name

class UserPlaylist(): 
    __slots__ = ['name', 'idx', 'uri', 'track_count']
    def __init__(self, name, idx, uri, track_count):
        self.name = name
        self.idx = idx
        self.uri = uri
        self.track_count = track_count

    def __str__(self):
        return self.name

class SearchResults():
    __slots__ = ['tracks', 'artists', 'albums', 'album_track_map']
    def __init__(self, tracks, artists, albums, album_track_map):
        self.tracks = tracks
        self.artists = artists
        self.albums = albums
        self.album_track_map = album_track_map

scope = "user-follow-read," \
        "user-library-read," \
        "user-library-modify," \
        "user-modify-playback-state," \
        "user-read-playback-state," \
        "user-read-currently-playing," \
        "app-remote-control," \
        "playlist-read-private," \
        "playlist-read-collaborative," \
        "playlist-modify-public," \
        "playlist-modify-private," \
        "streaming"

DATASTORE = datastore.Datastore()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


pageSize = 50
has_internet = False

def check_internet(request):
    global has_internet
    try:
        result = request()
        has_internet = True
    except Exception as _:
        print("no ints")
        result = None
        has_internet = False
    return result

def get_playlist(id):
    # TODO optimize query
    results = sp.playlist(id)
    tracks = []
    for _, item in enumerate(results['tracks']['items']):
        track = item['track']
        tracks.append(UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
    return (UserPlaylist(results['name'], 0, results['uri'], len(tracks)), tracks) # return playlist index as 0 because it won't have a idx parameter when fetching directly from Spotify (and we don't need it here anyway)

def get_show(id):
    results = sp.show(id)
    show = results['name']
    publisher = results['publisher']
    episodes = []
    for _, item in enumerate(results['episodes']['items']):
        episodes.append(UserEpisode(item['name'], publisher, show, item['uri']))
    return (UserShow(results['name'], publisher, len(episodes), results['uri']), episodes)

def get_album(id):
    # TODO optimize query
    results = sp.album(id)
    album = results['name']
    artist = results['artists'][0]['name']
    tracks = []
    for _, item in enumerate(results['tracks']['items']):
        tracks.append(UserTrack(item['name'], artist, album, item['uri']))
    return (UserAlbum(results['name'], artist, len(tracks), results['uri']), tracks)


'''
def get_playlist_tracks(id):
    tracks = []
    results = sp.playlist_tracks(id, limit=pageSize)
    while(results['next']):
        for _, item in enumerate(results['items']):
            track = item['track']
            tracks.append(UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
        results = sp.next(results)
    for _, item in enumerate(results['items']):
        track = item['track']
        tracks.append(UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
    return tracks
'''

def get_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    items = results['items']
    while results['next']:
        results = sp.next(results)
        items.extend(results['items'])
    for item in items:
        track = item['track']
        if track:
            artist_name = None
            if track.get('artists') and len(track['artists']) > 0 and track['artists'][0].get('name'):
                artist_name = track['artists'][0]['name']

            album_name = None
            if track.get('album') and track['album'].get('name'):
                album_name = track['album']['name']

            track_uri = track.get('uri')
            track_name = track.get('name')

            if track_name and artist_name and album_name and track_uri:
                tracks.append(UserTrack(track_name, artist_name, album_name, track_uri))
            else:
                print(f"Skipping track due to missing data: {track}")
    return tracks



def get_album_tracks(id):
    tracks = []
    results = sp.playlist_tracks(id, limit=pageSize)
    while(results['next']):
        for _, item in enumerate(results['items']):
            track = item['track']
            tracks.append(UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
        results = sp.next(results)
    for _, item in enumerate(results['items']):
        track = item['track']
        tracks.append(UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
    return tracks

def refresh_devices():
    results = sp.devices()
    DATASTORE.clearDevices()
    for _, item in enumerate(results['devices']):
        if "raspotify (SpotPod)" in item['name']:
            print(item['name'])
            device = UserDevice(item['id'], item['name'], item['is_active'])
            DATASTORE.setUserDevice(device)


#def refresh_devices():
#    device = UserDevice('5f0a2846b24414b0e350ba2386578f8cba59c528','raspotify (SpotPod2)', True)
#    DATASTORE.setUserDevice(device)

def parse_album(album):
    artist = album['artists'][0]['name']
    tracks = []
    if 'tracks' not in album :
        return get_album(album['id'])
    for _, track in enumerate(album['tracks']['items']):
        tracks.append(UserTrack(track['name'], artist, album['name'], track['uri']))
    return (UserAlbum(album['name'], artist, len(tracks), album['uri']), tracks)

def parse_show(show):
    publisher = show['publisher']
    episodes = []
    if 'episodes' not in show :
        return get_show(show['id'])
    for _, episode in enumerate(show['episodes']['items']):
        episodes.append(UserEpisode(episode['name'], publisher, show['name'], episode['uri']))
    return (UserShow(show['name'], publisher, len(episodes), show['uri']), episodes)
    
def refresh_data():
    DATASTORE.clear()
    results = sp.current_user_saved_tracks(limit=pageSize, offset=0)
    while(results['next']):
        offset = results['offset']
        for idx, item in enumerate(results['items']):
            track = item['track']
            DATASTORE.setSavedTrack(idx + offset, UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))
        results = sp.next(results)

    offset = results['offset']
    for idx, item in enumerate(results['items']):
        track = item['track']
        DATASTORE.setSavedTrack(idx + offset, UserTrack(track['name'], track['artists'][0]['name'], track['album']['name'], track['uri']))

    print("Spotify tracks fetched")

    offset = 0
    results = sp.current_user_followed_artists(limit=pageSize)
    while(results['artists']['next']):
        for idx, item in enumerate(results['artists']['items']):
            DATASTORE.setArtist(idx + offset, UserArtist(item['name'], item['uri']))
        results = sp.next(results['artists'])
        offset = offset + pageSize

    for idx, item in enumerate(results['artists']['items']):
        DATASTORE.setArtist(idx + offset, UserArtist(item['name'], item['uri']))

    print("Spotify artists fetched: " + str(DATASTORE.getArtistCount()))

    results = sp.current_user_playlists(limit=pageSize)
    totalindex = 0 # variable to preserve playlist sort index when calling offset loop down below
    while(results['next']):
        offset = results['offset']
        for idx, item in enumerate(results['items']):
            tracks = get_playlist_tracks(item['id'])
            DATASTORE.setPlaylist(UserPlaylist(item['name'], totalindex, item['uri'], len(tracks)), tracks, index=idx + offset)
            totalindex = totalindex + 1
        results = sp.next(results)

    offset = results['offset']
    for idx, item in enumerate(results['items']):
        tracks = get_playlist_tracks(item['id'])
        DATASTORE.setPlaylist(UserPlaylist(item['name'], totalindex, item['uri'], len(tracks)), tracks, index=idx + offset)
        totalindex = totalindex + 1

    print("Spotify playlists fetched: " + str(DATASTORE.getPlaylistCount()))

    results = sp.current_user_saved_albums(limit=pageSize)
    while(results['next']):
        offset = results['offset']
        for idx, item in enumerate(results['items']):
            album, tracks = parse_album(item['album'])
            DATASTORE.setAlbum(album, tracks, index=idx + offset)
        results = sp.next(results)

    offset = results['offset']
    for idx, item in enumerate(results['items']):
        album, tracks = parse_album(item['album'])
        DATASTORE.setAlbum(album, tracks, index=idx + offset)

    print("Refreshed user albums")

    results = sp.new_releases(limit=pageSize)
    for idx, item in enumerate(results['albums']['items']):
        album, tracks = parse_album(item)
        DATASTORE.setNewRelease(album, tracks, index=idx)

    print("Refreshed new releases")

    results = sp.current_user_saved_shows(limit=pageSize)
    if(len(results['items']) > 0):
        offset = results['offset']
        for idx, item in enumerate(results['items']):
            show, episodes = parse_show(item['show'])
            DATASTORE.setShow(show, episodes, index=idx)

    print("Spotify Shows fetched")

    refresh_devices()
    print("Refreshed devices")

def play_artist(artist_uri, device_id = None):
    if (not device_id):
        devices = DATASTORE.getAllSavedDevices()
        if (len(devices) == 0):
            print("error! no devices")
            return
        device_id = devices[0].id
    response = sp.start_playback(device_id=device_id, context_uri=artist_uri)
    refresh_now_playing()
    print(response)

def play_track(track_uri, device_id = None):
    if (not device_id):
        devices = DATASTORE.getAllSavedDevices()
        if (len(devices) == 0):
            print("error! no devices")
            return
        device_id = devices[0].id
    sp.start_playback(device_id=device_id, uris=[track_uri])

def play_episode(episode_uri, device_id = None):
    if(not device_id):
        devices = DATASTORE.getAllSavedDevices()
        if(len(devices) == 0):
            print("error! no devices")
            return
        device_id = devices[0].id
    sp.start_playback(device_id=device_id, uris=[episode_uri])

def play_from_playlist(playist_uri, track_uri, device_id = None):
    print("playing ", playist_uri, track_uri)
    if (not device_id):
        devices = DATASTORE.getAllSavedDevices()
        if (len(devices) == 0):
            print("error! no devices")
            return
        device_id = devices[0].id
    sp.start_playback(device_id=device_id, context_uri=playist_uri, offset={"uri": track_uri})
    refresh_now_playing()

def play_from_show(show_uri, episode_uri, device_id = None):
    print("playing ", show_uri, episode_uri)
    if(not device_id):
        devices = DATASTORE.getAllSavedDevices()
        if (len(devices) == 0):
            print("error! no devices")
            return
        device_id = devices[0].id
    sp.start_playback(device_id=device_id, context_uri=show_uri, offset={"uri": episode_uri})
    refresh_now_playing()

def get_now_playing():
    response = check_internet(lambda: sp.current_playback(additional_types='episode'))
    if (not response):
        return None

    if (response['currently_playing_type'] == 'episode'):
        return get_now_playing_episode(response = response)
    else:
        return get_now_playing_track(response = response)

def get_now_playing_track(response = None):
    if(not response or not response['item']):
        return None

    context = response['context']
    track = response['item']
    track_uri = track['uri']
    artist = track['artists'][0]['name']
    now_playing = {
        'name': track['name'],
        'track_uri': track_uri,
        'artist': artist,
        'album': track['album']['name'],
        'duration': track['duration_ms'],
        'is_playing': response['is_playing'],
        'progress': response['progress_ms'],
        'context_name': artist,
        'track_index': -1,
        'timestamp': time.time()
    }
    if not context:
        return now_playing
    if (context['type'] == 'playlist'):
        uri = context['uri']
        playlist = DATASTORE.getPlaylistUri(uri)
        tracks = DATASTORE.getPlaylistTracks(uri)
        if (not playlist):
            playlist, tracks = get_playlist(uri.split(":")[-1])
            DATASTORE.setPlaylist(playlist, tracks)
        now_playing['track_index'] = next(x for x, val in enumerate(tracks) 
                                  if val.uri == track_uri) + 1
        now_playing['track_total'] = len(tracks)
        now_playing['context_name'] = playlist.name
    elif (context['type'] == 'album'):
        uri = context['uri']
        album = DATASTORE.getAlbumUri(uri)
        tracks = DATASTORE.getPlaylistTracks(uri)
        if (not album):
            album, tracks = get_album(uri.split(":")[-1])
            DATASTORE.setAlbum(album, tracks)
        now_playing['track_index'] = next(x for x, val in enumerate(tracks) 
                                  if val.uri == track_uri) + 1
        now_playing['track_total'] = len(tracks)
        now_playing['context_name'] = album.name
    return now_playing

def get_now_playing_episode(response = None):
    if(not response or not response['item']):
        return None

    episode = response['item']
    episode_uri = episode['uri']
    publisher = episode['show']['publisher']
    now_playing = {
        'name': episode['name'],
        'track_uri': episode_uri,
        'artist': publisher,
        'album': episode['show']['name'],
        'duration': episode['duration_ms'],
        'is_playing': response['is_playing'],
        'progress': response['progress_ms'],
        'context_name': publisher,
        'track_index': -1,
        'timestamp': time.time()
    }
    
    return now_playing

def search(query):
    track_results = sp.search(query, limit=5, type='track')
    tracks = []
    for _, item in enumerate(track_results['tracks']['items']):
        tracks.append(UserTrack(item['name'], item['artists'][0]['name'], item['album']['name'], item['uri']))
    artist_results = sp.search(query, limit=5, type='artist')
    artists = []
    for _, item in enumerate(artist_results['artists']['items']):
        artists.append(UserArtist(item['name'], item['uri']))
    album_results = sp.search(query, limit=5, type='album')
    albums = []
    album_track_map = {}
    for _, item in enumerate(album_results['albums']['items']):
        album, album_tracks = parse_album(item)
        albums.append(album)
        album_track_map[album.uri] = album_tracks
    return SearchResults(tracks, artists, albums, album_track_map)

def refresh_now_playing():
    DATASTORE.now_playing = get_now_playing()

def play_next():
    global sleep_time
    sp.next_track()
    sleep_time = 0.4
    refresh_now_playing()

def play_previous():
    global sleep_time
    sp.previous_track()
    sleep_time = 0.4
    refresh_now_playing()

def pause():
    global sleep_time
    sp.pause_playback()
    sleep_time = 0.4
    refresh_now_playing()

def resume():
    global sleep_time
    sp.start_playback()
    sleep_time = 0.4
    refresh_now_playing()

def toggle_play():
    now_playing = DATASTORE.now_playing
    if not now_playing:
        return
    if now_playing['is_playing']:
        pause()
    else:
        resume()

def bg_loop():
    global sleep_time
    while True:
        refresh_now_playing()
        time.sleep(sleep_time)
        sleep_time = min(4, sleep_time * 2)

sleep_time = 0.3
thread = threading.Thread(target=bg_loop, args=())
thread.daemon = True                            # Daemonize thread
thread.start()

def run_async(fun):
    threading.Thread(target=fun, args=()).start()
