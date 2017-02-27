import os
import time
from functools import wraps

from flask import (Flask, redirect, url_for, session,
                   request, render_template)
from flask_oauthlib.client import OAuth, OAuthException
from flask_sslify import SSLify

SPOTIFY_APP_ID = os.environ.get('SPOTIFY_APP_ID')
SPOTIFY_APP_SECRET = os.environ.get('SPOTIFY_APP_SECRET')
SECRET_KEY = os.environ.get('SPOTIFY_KEY')

app = Flask(__name__)
app.secret_key = SECRET_KEY
oauth = OAuth(app)
sslify = SSLify(app)

spotify_scopes = [
    'playlist-read-private',
    'user-read-private',
    'playlist-modify-private',
    'playlist-modify-public',
]
spotify_scope_str = ' '.join(spotify_scopes)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': spotify_scope_str},
    base_url='https://api.spotify.com/v1/',
    request_token_url=None,
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    content_type='application/json',
)


@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        oauth_token = session.get('oauth_token')
        expire = session.get('expire')
        if not oauth_token:
            return redirect(url_for('login'))
        elif expire < time.time():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

"""
Routes
"""


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/login')
def login():
    callback = url_for(
        'spotify_authorized',
        next=request.args.get('next') or None,
        _external=True
    )
    return spotify.authorize(callback=callback)


@app.route('/login/authorized')
def spotify_authorized():
    resp = spotify.authorized_response()
    if resp is None:
        return 'Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: {0}'.format(resp.message)

    session['oauth_token'] = (resp['access_token'], '')
    me = spotify.get('me')
    session['user_id'] = me.data['id']
    session['expire'] = time.time() + 3500  # roughly 1 hour
    return redirect(url_for('index'))


@app.route('/playlists')
@requires_login
def playlists():
    user_id = session.get('user_id')
    resp = spotify.get('users/{user_id}/playlists'.format(user_id=user_id))
    playlists = resp.data['items']
    return render_template('playlists.html', playlists=playlists)


@app.route('/artists')
@requires_login
def artists():
    q = request.args.get('q', 'pitbull')
    get_data = {
        'market': 'from_token',
        'type': 'artist',
        'q': q,
    }
    if q:
        resp = spotify.get('search/', data=get_data)
        artists = resp.data['artists']['items']
    else:
        artists = []
    return render_template('artists.html', artists=artists, q=q)


@app.route('/artists/related/<artist_id>')
@requires_login
def related_artists(artist_id):
    """Returns the list of related artists to the given
    artist_id
    """
    artists = get_related_artists(artist_id)
    return render_template('artists.html', artists=artists)


@app.route('/artists/related-tracks/<artist_id>')
@requires_login
def related_tracks(artist_id):
    """Given an artist_id, gets related artists, then
    their top tracks
    """
    resp = spotify.get('artists/{0}'.format(artist_id))
    artist_name = resp.data['name']
    related_artists = get_related_artists(artist_id)
    track_collection = []
    track_uris = []
    for artist in related_artists:
        tracks = get_top_tracks(artist['id'])[:3]
        track_collection.extend(tracks)
        track_uris.extend([track['uri'] for track in tracks])

    track_uri_str = ','.join(track_uris)
    return render_template('tracks.html',
                           tracks=track_collection,
                           track_uri_str=track_uri_str,
                           artist_name=artist_name)


@app.route('/playlists/new', methods=['POST'])
@requires_login
def new_playlist():
    """Given POST data of artist_id
    creates a new playlist based off of this artists
    related artists
    """
    playlist_name = request.form['playlist_name']
    public = request.form['public']
    track_uris = request.form['track_uris'].split(',')
    new_playlist_data = {
        'name': playlist_name,
        'public': public
    }

    user_id = session.get('user_id')
    resp = spotify.post('users/{0}/playlists'.format(user_id),
                        data=new_playlist_data,
                        format='json')
    if str(resp.status).startswith('2'):
        href = resp.data['href']
        href += '/tracks'  # to add new tracks
        resp = spotify.post(href,
                            data={'uris': track_uris},
                            format='json')
        print(resp.data)
        return redirect(url_for('playlists'))
    return redirect(url_for('artists'))


def get_related_artists(artist_id):
    """Given the artist_id, gets related ones
    """
    resp = spotify.get('artists/{0}/related-artists'.format(artist_id))
    artists = resp.data['artists']
    return artists


def get_top_tracks(artist_id):
    """Given artist_id, gets top tracks for artist
    """
    get_data = {'country': 'US'}
    resp = spotify.get('artists/{0}/top-tracks'.format(artist_id),
                       data=get_data)
    tracks = resp.data['tracks']
    return tracks


if __name__ == '__main__':
    app.debug = True
    app.run()
