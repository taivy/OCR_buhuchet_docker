#!/bin/sh
from flask import Flask, render_template, request, jsonify, make_response
from pdf2image import convert_from_bytes
import io
import os
import json
from PIL import Image
from werkzeug.contrib.fixers import ProxyFix

from yandex_ocr_request_func import get_yandex_cloud_ocr_response
from ocr_funcs import ocr_buhuchet
from crop import crop_frames


SAVE_IMAGES_MODE = os.environ.get('SAVE_IMAGES_MODE')
DEBUG_MODE = os.environ.get('DEBUG_MODE')
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'bmp'])

app = Flask(__name__)


def merge_dicts(dict1, dict2): 
    dict1.update(dict2)

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
            result = dict()
            i = 0
            for page in pages:
                cropped_page = crop_frames(page, i=i)
                imgByteArr = io.BytesIO()
                cropped_page.save(imgByteArr, format='PNG')
                img_data = imgByteArr.getvalue()
                response_path = os.path.join(file_images_dir, "%s_response.json" % str(i))
                resp = None
                if not resp:
                    resp = get_yandex_cloud_ocr_response(img_data)
                    resp_error = check_response(resp)
                    if resp_error is not None:
                        if "Image size exceededs limitation" in resp_error['message']:
                            err_i = 0
                            while resp_error and err_i < 10:
                                #print("Image size exceededs limitation")
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
                    merge_dicts(result, r)
                i+=1         
        else:
            img_data = f.read()
            response_path = os.path.join(file_images_dir, "response.json")
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
        return make_response(jsonify(result), 200)
    
    
app.wsgi_app = ProxyFix(app.wsgi_app)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
