from flask import Flask, jsonify, request
import folium
import math
import os
import time
import boto3
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from folium.features import DivIcon

app = Flask(__name__)

# AWS credentials and settings
ACCESS_KEY = 'LWJLY6W5D9L6RRBC8YAW'
AWS_SECRET_ACCESS_KEY = 'cKVCaizO0fZ52EDdFEVHDrR3Xg4q52tcSOvBBVl1'
BUCKET_NAME = 'circles-on-map'
AWS_REGION = 's3'
AWS_S3_ENDPOINT_URL = 'https://s3.eu-central-1.wasabisys.com'
AWS_QUERYSTRING_AUTH = False

# Initialize boto3 client for S3
s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION, endpoint_url=AWS_S3_ENDPOINT_URL)

def create_map(latitude, longitude, radius, icon, labels_in_local_lang, text, markers):
    # Calculate the zoom level
    zoom_start = 16 - math.log(radius*2/1000)/math.log(2)

    # Choose the map style
    if labels_in_local_lang:
        tiles = 'OpenStreetMap'
    else:
        tiles = 'https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=w1KzgwhuJAABSC7CEAg4'

    # Create a map centered at your coordinates
    m = folium.Map(
        location=[latitude, longitude],
        zoom_start=zoom_start,
        control_scale=False,
        zoom_control=False,
        tiles=tiles,  # Use the chosen map style
        attr='MapTiler'
    )

    # Map the icon to the correct string
    icon_mapping = {
        "car": "car",
        "boat": "ship",
        "yacht": "sailboat",
        "seaplane": "plane-departure",
        "plane": "plane",
        "ferry": "ferry",
        "resort-hotel": "ranking-star",
        "hotel": "bell-concierge",
    }
    icon = icon_mapping.get(icon, "car")

    # Add a marker at the center
    folium.Marker(
        location=[latitude, longitude],
        icon=folium.Icon(icon=icon, prefix='fa'),
    ).add_to(m)

    # Add a label that will always be displayed
    folium.map.Marker(
        [latitude, longitude],
        icon=DivIcon(
            icon_size=(150,36),
            icon_anchor=(0,0),
            html='<div style="font-size: 10pt; '
                 'color: white; '
                 'background-color: rgba(0, 0, 0, 0.7); '
                 'padding: 6px; '
                 'box-shadow: rgba(0, 0, 0, 0.4) 5px 5px, rgba(0, 0, 0, 0.3) 10px 10px, rgba(0, 0, 0, 0.2) 15px 15px, rgba(0, 0, 0, 0.1) 20px 20px, rgba(0, 0, 0, 0.05) 25px 25px; '
                 'border-radius: 0 100px 100px 100px;'
                 'display: inline-block;'
                 'font-weight: bold;'
                 f'font-style: oblique;">{text}</div>',
            )
        ).add_to(m)

    # Add additional markers
    for marker in markers:
        marker_icon = icon_mapping.get(marker['icon'], "car")
        folium.Marker(
            location=[marker['latitude'], marker['longitude']],
            icon=folium.Icon(icon=marker_icon, prefix='fa'),
        ).add_to(m)
        # Add a label that will always be displayed
        folium.map.Marker(
            location=[marker['latitude'], marker['longitude']],
            icon=DivIcon(
                icon_size=(150, 36),
                icon_anchor=(0, 0),
                html='<div style="font-size: 10pt; '
                     'color: white; '
                     'background-color: rgba(0, 0, 0, 0.7); '
                     'padding: 6px; '
                     'box-shadow: rgba(0, 0, 0, 0.4) 5px 5px, rgba(0, 0, 0, 0.3) 10px 10px, rgba(0, 0, 0, 0.2) 15px 15px, rgba(0, 0, 0, 0.1) 20px 20px, rgba(0, 0, 0, 0.05) 25px 25px; '
                     'border-radius: 0 100px 100px 100px;'
                     'display: inline-block;'
                     'font-weight: bold;'
                     f'font-style: oblique;">{marker["text"]}</div>',
            )
        ).add_to(m)

    # Add a circle to the map
    folium.Circle(
        location=[latitude, longitude],
        radius=radius,
        color='green',
        fill=True,
        fill_color='green'
    ).add_to(m)

    # Remove the attribution text
    m.get_root().html.add_child(folium.Element("<style>.leaflet-control-attribution {display: none;}</style>"))

    # Save the map to an HTML file
    m.save('map.html')

def create_picture_of_a_map():
    # Create a new instance of the browser driver
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    # Get the absolute path of 'map.html'
    map_html_path = os.path.abspath('map.html')

    # Open the HTML file in the web browser
    driver.get('file://' + map_html_path)
    # Wait for the map to load
    time.sleep(1.5)

    # Generate a unique filename for the screenshot
    filename = 'map_' + str(uuid.uuid4()) + '.png'
    # Take a screenshot and save it
    driver.save_screenshot(filename)
    driver.quit()

    # Delete the 'map.html' file
    os.remove(map_html_path)
    return filename


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'success', 'message': 'pong'})


@app.route('/map-picture', methods=['POST'])
def get_map_picture():
    data = request.get_json()
    latitude = data['latitude']
    longitude = data['longitude']
    radius = data['radius']
    icon = data['icon']
    labels_in_local_lang = data.get('labels-in-local-lang', False)
    text = data['text']
    markers = data.get('markers', [])
    radius *= 1000  # To turn KM into M

    create_map(latitude, longitude, radius, icon, labels_in_local_lang, text, markers)
    filename = create_picture_of_a_map()

    with open(filename, 'rb') as data:
        s3.upload_fileobj(data, BUCKET_NAME, filename)

    # Delete the local picture file after uploading it to S3
    os.remove(filename)

    s3_url = f"{AWS_S3_ENDPOINT_URL}/{BUCKET_NAME}/{filename}"
    return jsonify({'url': s3_url})

if __name__ == '__main__':
    app.run(debug=True)
