from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth, OAuthException


SPOTIFY_APP_ID = '13b35efe8dcb4d2aa56d9e3ebf97e90c'
SPOTIFY_APP_SECRET = 'a441c68707d04cc691d4ca1888cda585'


app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': 'user-read-email playlist-read-private'},
    base_url='https://api.spotify.com/v1/',
    request_token_url=None,
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize'
)


@app.route('/')
def index():
    return redirect(url_for('login'))


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
    return 'Logged in as id={0} display_name={1}, uri="{2}", redirect={3}'.format(
        me.data['id'],
        me.data['display_name'],
        me.data['uri'],
        request.args.get('next')
    )

@app.route('/api/playlists')
def api_playlists():
    resp = spotify.authorized_response()
    me = spotify.get('me')
    user_id = me.data['id']
    playlists = spotify.get('users/{user_id}/playlists'.format(user_id=user_id))
    return jsonify(playlists.data)

@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


if __name__ == '__main__':
    app.run()
