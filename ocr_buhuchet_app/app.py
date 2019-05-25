#!/bin/sh


from flask import Flask, render_template, request, jsonify
from pdf2image import convert_from_bytes
import io
from itertools import chain
import os
from werkzeug.contrib.fixers import ProxyFix

from yandex_ocr_request_func import get_yandex_cloud_ocr_response
from ocr_funcs import ocr_buhuchet
from crop import crop_frames



SAVE_IMAGES_MODE = True
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'bmp'])

app = Flask(__name__)



@app.route('/')
def main():
    return render_template('index.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        print(request)
        print(request.files)
        print(request.files['file'])
        f = request.files['file']
        if SAVE_IMAGES_MODE:
            # filename wihtout extension
            filename = f.filename[:f.filename.find('.')]
            file_images_dir = os.path.join('images', filename)
            if not os.path.exists(file_images_dir):
                os.mkdir(file_images_dir)
        if f.mimetype.endswith('pdf'):
            pages = convert_from_bytes(f.read())
            result = []
            i = 0
            for page in pages:
                cropped_page = crop_frames(page, i=i)
                imgByteArr = io.BytesIO()
                cropped_page.save(imgByteArr, format='PNG')
                resp = get_yandex_cloud_ocr_response(imgByteArr.getvalue())
                if SAVE_IMAGES_MODE:
                    image_path = os.path.join(file_images_dir, "%s_image.jpg" % str(i))
                    cropped_page.save(image_path, "JPEG") 
                    response_path = os.path.join(file_images_dir, "%s_response.json" % str(i))
                    with open(response_path, 'w') as outf:
                        outf.write(resp)
                r = ocr_buhuchet(resp, debug_mode=False)
                result = list(chain(result, [r]))
                i+=1                
        else:
            image_data = f.read()
            resp = get_yandex_cloud_ocr_response(image_data)
            if SAVE_IMAGES_MODE:
                image_path = os.path.join(file_images_dir, "image.jpg")
                with open(image_path, 'wb') as outf:
                    outf.write(image_data)
                response_path = os.path.join(file_images_dir, "response.json")
                with open(response_path, 'w') as outf:
                    outf.write(resp)
            r = ocr_buhuchet(resp)
            result = r
        return jsonify(result)

app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
