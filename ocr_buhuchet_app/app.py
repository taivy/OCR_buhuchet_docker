#!/bin/sh


from flask import Flask, render_template, request, jsonify
from pdf2image import convert_from_bytes
import io
from itertools import chain
import os
import json
from PIL import Image
from werkzeug.contrib.fixers import ProxyFix

from yandex_ocr_request_func import get_yandex_cloud_ocr_response
from ocr_funcs import ocr_buhuchet
from crop import crop_frames


SAVE_IMAGES_MODE = True
DEBUG_MODE = False
USE_RESPONSE_CACHE = False
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'bmp'])

app = Flask(__name__)


def check_response(resp):
    try:
        data = json.loads(resp)['results'][0]
    except:
        raise RuntimeError('Error in JSON response: no results')
    error = data.get('error', None)
    if error is not None:
        if "Image size exceededs limitation" in error['message']:
            return error
        else:
            raise RuntimeError('Error in JSON response:  %s' % error['message'])
            

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        filepath = request.headers['Filepath']
        f = open(filepath, 'rb')
        if SAVE_IMAGES_MODE:
            # filename wihtout extension
            filename = filepath[:filepath.find('.')]
            file_images_dir = os.path.join('images', filename)
            if not os.path.exists(file_images_dir):
                os.mkdir(file_images_dir)
        if filepath.endswith('pdf'):
            pages = convert_from_bytes(f.read())
            result = []
            i = 0
            for page in pages:
                cropped_page = crop_frames(page, i=i)
                imgByteArr = io.BytesIO()
                cropped_page.save(imgByteArr, format='PNG')
                img_data = imgByteArr.getvalue()
                response_path = os.path.join(file_images_dir, "%s_response.json" % str(i))
                resp = None
                if USE_RESPONSE_CACHE:
                    if os.path.exists(response_path):
                        with open(response_path, 'r') as f:
                            resp = f.read()
                if not resp:
                    # если используется кэш, то файл в response_path пустой, 
                    # нужно заново получать
                    resp = get_yandex_cloud_ocr_response(img_data)
                    resp_error = check_response(resp)
                    if resp_error is not None:
                        if "Image size exceededs limitation" in resp_error['message']:
                            err_i = 0
                            # избегаем бесконечного цикла (может появиться и другая ошибка)
                            while resp_error and err_i < 10:
                                
                                print("Image size exceededs limitation")
                                cropped_page.thumbnail((1000, 1000), Image.ANTIALIAS)
                                cropped_page.save('ke.jpg', "JPEG")
                                imgByteArr = io.BytesIO()
                                cropped_page.save(imgByteArr, format='PNG')
                                img_data = imgByteArr.getvalue()
                                resp = get_yandex_cloud_ocr_response(img_data)
                                resp_error = check_response(resp)
                                err_i += 1
                if SAVE_IMAGES_MODE:
                    image_path = os.path.join(file_images_dir, "%s_image.jpg" % str(i))
                    cropped_page.save(image_path, "JPEG") 
                    img_for_debug_path = image_path
                    with open(response_path, 'w') as outf:
                        outf.write(resp)
                r = ocr_buhuchet(resp, debug_mode=DEBUG_MODE, img_path=img_for_debug_path)
                if r:
                    result = list(chain(result, [r]))
                    print(result)
                i+=1         
            return jsonify(result)
        else:
            img_data = f.read()
            response_path = os.path.join(file_images_dir, "response.json")
            if USE_RESPONSE_CACHE:
                if os.path.exists(response_path):
                    with open(response_path, 'r') as f:
                        resp = f.read()
                        if not resp:
                            resp = get_yandex_cloud_ocr_response(img_data)
                else:
                    resp = get_yandex_cloud_ocr_response(img_data)
            else:
                resp = get_yandex_cloud_ocr_response(img_data)
            if SAVE_IMAGES_MODE:
                image_path = os.path.join(file_images_dir, "image.jpg")
                with open(image_path, 'wb') as outf:
                    outf.write(img_data)
                img_for_debug_path = image_path
                with open(response_path, 'w') as outf:
                    outf.write(resp)
            r = ocr_buhuchet(resp, debug_mode=DEBUG_MODE, img_path=img_for_debug_path)
            result = r
            return jsonify(result)
        return jsonify(result)
    
    
app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
