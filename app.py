import os
import gpxpy
import numpy as np
import pandas as pd
import geo
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from gpxpy.geo import distance, Location
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'gpx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_gpx(filename):
    gpx_file = open(filename)
    gpx = gpxpy.parse(gpx_file)
    if gpx.tracks:
        points = [p for s in gpx.tracks[0].segments for p in s.points]
    else:
        points = [p for p in gpx.routes[0].points]
    return points

def elev_smoothed(points, threshold):
    ''' Returns elevation gain, counting only changes above threshold between points '''

    # if points lack elevation, return 'No data'
    if points[0].elevation is None:
        return 'No data'

    elevs = []
    last_elev = points[0].elevation
    elevs.append(last_elev)
    for p in points:
        if np.abs(p.elevation - last_elev) >= threshold:
            last_elev = p.elevation
            elevs.append(last_elev)

    elev_change = 0
    for i in range(len(elevs) - 1):
        if elevs[i+1] - elevs[i] > 0:
            elev_change += elevs[i+1] - elevs[i]

    return round(elev_change)

def gpx_stats(points):
    if points[0].time is None:
        start = 'No data'
        finish = 'No data'
        elapsed = 'No data'
        min_interval = 'No data'
    else:
        start = points[0].time
        finish = points[-1].time
        elapsed = finish - start

        intervals = [points[i+1].time - points[i].time for i in range(0, len(points) - 1)]
        min_interval = '{} sec'.format(min(intervals).seconds)

    dists = [distance(points[i].latitude, points[i].longitude, None, points[i+1].latitude, points[i+1].longitude, None) for i in range(0, len(points) - 1)]
    total_dist_km = '{}km'.format(round(sum(dists)/1000, 2))
    total_dist_mi = '{}mi'.format(round(sum(dists)/1609.34, 2))

    elev_change = '{}m/{}m (2m/10m threshold)'.format(elev_smoothed(points, 2), elev_smoothed(points, 10))

    loop_bool = geo.is_loop(points, 100)

    start_lat = points[0].latitude
    start_lon = points[0].longitude

    return start, start_lat, start_lon, finish, elapsed, min_interval, total_dist_km, total_dist_mi, elev_change, loop_bool

def to_dataframe(points):
    latitudes = [points[i].latitude for i in range(0, len(points))]
    longitudes = [points[i].longitude for i in range(0, len(points))]

    cum_dists = []
    cum_dist = 0
    cum_dists.append(cum_dist)
    for i in range(len(points) - 1):
        cum_dist += distance(points[i].latitude, points[i].longitude, None, points[i+1].latitude, points[i+1].longitude, None)
        cum_dists.append(cum_dist)

    elevations = [points[i].elevation for i in range(0, len(points))]
    times = [points[i].time for i in range(0, len(points))]
    return pd.DataFrame({'lat': latitudes, 'lon': longitudes, 'cum_dist': cum_dists, 'elev': elevations, 'time': times})

def folium_map(df):
    import folium   # (https://pypi.python.org/pypi/folium)
    mymap = folium.Map()
    i = 0
    for coord in df[['lat','lon','cum_dist']].values:
        if i < 5:
            color='green'
        elif 5 <= i < 10:
            color='yellow'
        else:
            color='red'
        folium.CircleMarker(location=[coord[0],coord[1]], radius=1,color=color,
                            tooltip=f'{coord[0]:.5f}, {coord[1]:.5f}, {coord[2]/1000:.2f}km').add_to(mymap)
        i += 1

    sw = df[['lat', 'lon']].min().values.tolist()
    ne = df[['lat', 'lon']].max().values.tolist()
    mymap.fit_bounds([sw, ne])

    return mymap

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            points = parse_gpx(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            start, start_lat, start_lon, finish, elapsed, min_interval, total_dist_km, total_dist_mi, elev_change, loop_bool = gpx_stats(points)

            # delete file so it does not clog space
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            points_even = geo.interpolate_distance(points, 50)
            df_even = to_dataframe(points_even)

            map = folium_map(df_even)

            map.save('templates/map.html')
            map_path = 'map.html'

            return render_template('result.html',
                name = filename,
                start = start,
                start_lat = start_lat,
                start_lon = start_lon,
                finish = finish,
                elapsed = elapsed,
                min_interval = min_interval,
                total_dist_km = total_dist_km,
                total_dist_mi = total_dist_mi,
                elev_change = elev_change,
                loop_bool = loop_bool,
                map = map_path)
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

#@app.route('/home/pi/GPX/webapp/uploads/<filename>')
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/map.html')
def map():
    return render_template('map.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
