import requests, slumber

ENDPOINT_URL = 'https://api.spotify.com/v1/'

spotify = slumber.API(ENDPOINT_URL, format='json', append_slash=False)

def get_related_tracks(artist_id):
    """Given an artist_id, gets the top track uris for this artists
    related artists.

    """
    this_artist = spotify.artists(artist_id).get()
    related_artists = spotify.artists(this_artist['id'])('related-artists').get()['artists']

    related_tracks = []
    for ra in related_artists:
        ra_id = ra['id']
        top_tracks = spotify.artists(ra_id)('top-tracks?country=US').get()['tracks']

        top_tracks_uris = [t['uri'] for t in top_tracks[0:2]]
        related_tracks.extend(top_tracks_uris)
    return related_tracks

if __name__ == '__main__':
    pitbull_id = '0TnOYISbd1XYRBk9myaseg'
    print(get_related_tracks(pitbull_id))
