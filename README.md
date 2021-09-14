# gpx-webapp
A simple GPX viewer web app using Flask.

## Installation
`pip install -r requirements.txt`

## Usage
1. Run `python app.py`.
2. Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000) to view the webapp.
3. Select a GPX file to upload, eg [example.gpx](https://github.com/mikedbjones/gpx-webapp/blob/main/examples/example.gpx).

The output includes:
- Time, location, distance and elevation stats
- Loop detection
- A map tile generated using Folium, including green/amber markers to show the start location. Note, markers are evenly spaced and reduced to improve map loading.

Example output:

![output](https://github.com/mikedbjones/gpx-webapp/blob/main/examples/example.png)
