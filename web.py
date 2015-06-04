from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from flask_oauthlib.client import OAuth, OAuthException

import simplejson as json


SPOTIFY_APP_ID = '13b35efe8dcb4d2aa56d9e3ebf97e90c'
SPOTIFY_APP_SECRET = 'a441c68707d04cc691d4ca1888cda585'
SECRET_KEY = ''

app = Flask(__name__)
oauth = OAuth(app)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': 'playlist-read-private user-read-private playlist-modify-private playlist-modify-public'},
    base_url='https://api.spotify.com/v1/',
    request_token_url=None,
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    content_type='application/json',
)


@app.route('/')
def index():
    if not session.get('oauth_token'):
        return redirect(url_for('login'))

    me = spotify.get('me')
    msg = "Authenticated as {} and email {}".format(me.data['id'], me.data['email'])
    return render_template('home.html')

@app.route('/session')
def session_test():
    return str(session.get('oauth_token'))

@app.route('/login')
def login():
    callback = url_for(
        'spotify_authorized',
        next=request.args.get('next') or request.referrer or None,
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
    session['user_id']= me.data['id']
    return redirect(url_for('index'))

@app.route('/playlists')
def playlists():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    resp = spotify.get('users/{user_id}/playlists'.format(user_id=user_id))
    playlists = resp.data['items']
    return render_template('playlists.html', playlists=playlists)

@app.route('/artists')
def artist():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    q = request.args.get('q', 'pitbull')
    get_data = {
        'market': 'from_token',
        'type': 'artist',
        'q': q,
    }
    resp = spotify.get('search/', data=get_data)
    artists = resp.data['artists']['items']
    return render_template('artists.html', artists=artists)

@app.route('/artists/related/<artist_id>')
def related_artists(artist_id):
    """Returns the list of related artists to the given 
    artist_id
    """
    artists = get_related_artists(artist_id)
    return render_template('artists.html', artists=artists)

@app.route('/artists/related-tracks/<artist_id>')
def related_tracks(artist_id):
    """Given an artist_id, gets related artists, then
    their top tracks
    """
    resp = spotify.get('artists/{0}'.format(artist_id))
    artist_name = resp.data['name']
    artists = get_related_artists(artist_id)
    track_collection = []
    track_uris = []
    for artist in artists:
        tracks = get_top_tracks(artist['id'])[:3]
        track_collection.extend(tracks)
        track_uris.extend([track['uri'] for track in tracks])
    
    track_uri_str = ','.join(track_uris)
    return render_template('tracks.html',
                           tracks=track_collection,
                           track_uri_str=track_uri_str,
                           artist_name=artist_name)

@app.route('/playlists/new', methods=['POST'])
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
        href += '/tracks' # to add new tracks
        resp = spotify.post(href,
                            data={'uris': track_uris},
                            format='json')
        print(resp.data)
        return redirect(url_for('playlists'))
    return redirect(url_for('artist'))

@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


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
    app.secret_key = 'development'
    app.run()
