import urllib, flask, re, hashlib

import os, sys, tempfile, shutil, contextlib, cv2, collections, mimetypes


@contextlib.contextmanager
def pushd_temp_dir(base_dir=None, prefix="tmp.hpo."):
    '''
    Create a temporary directory starting with {prefix} within {base_dir}
    and cd to it.

    This is a context manager.  That means it can---and must---be called using
    the with statement like this:

        with pushd_temp_dir():
            ....   # We are now in the temp directory
        # Back to original directory.  Temp directory has been deleted.

    After the with statement, the temp directory and its contents are deleted.


    Putting the @contextlib.contextmanager decorator just above a function
    makes it a context manager.  It must be a generator function with one yield. 

    - base_dir --- the new temp directory will be created inside {base_dir}.
                   This defaults to {main_dir}/data ... where {main_dir} is
                   the directory containing whatever .py file started the
                   application (e.g., main.py).

    - prefix ----- prefix for the temp directory name.  In case something
                   happens that prevents
    '''
    if base_dir is None:
        proj_dir = sys.path[0]
        # e.g., "/home/ecegridfs/a/ee364z15/hpo"

        main_dir = os.path.join(proj_dir, "data")
        # e.g., "/home/ecegridfs/a/ee364z15/hpo/data"

    # Create temp directory
    temp_dir_path = tempfile.mkdtemp(prefix=prefix, dir=base_dir)

    try:
        start_dir = os.getcwd()  # get current working directory
        os.chdir(temp_dir_path)  # change to the new temp directory

        try:
            yield
        finally:
            # No matter what, change back to where you started.
            os.chdir(start_dir)
    finally:
        # No matter what, remove temp dir and contents.
        shutil.rmtree(temp_dir_path, ignore_errors=True)


@contextlib.contextmanager
def fetch_images(etree):

    with pushd_temp_dir():
        filename_to_node = collections.OrderedDict()

        for node in etree.iter():
            img = node.find(".//img")
            if img is not None:
                img.make_links_absolute(img.base_url)
                get_img = urllib.request.Request(img.get("src"))
                get_img.add_header('User-Agent', 'PurdueUniversityClassProject/1.0 (srhie@purdue.edu https://goo.gl/dk8u5S)')
                fetch_img = urllib.request.urlopen(get_img)

                content_type = fetch_img.info().get("Content-type")
                extension = mimetypes.guess_extension(content_type)

                binary = img.get("src").encode('utf8')
                filename = make_filename(binary, extension)

                with open("%s" % filename, "wb") as outfile:
                    byte_img = fetch_img.read()
                    outfile.write(byte_img)

                filename_to_node[filename] = img
        # print(filename_to_node)
        yield filename_to_node


def get_image_info(filename):
    from PIL import Image
    # How to handle image format that's not supported by opencv
    # if filename contains .gif
    #   open filename using Pillow Image module
    #   Pillow.Image module here converts the image with RGB mode, suitable for jpg
    #   save image with jpg extension
    #   now opencv2 can read the tmp.jpg
    #   opencv2.shape returns a tuple of 3 elements, height, width, and channel
    #   take first two information and store it into h, w
    # else
    #   skip PIL.Image conversion
    #   but do the same
    #
    # Credit: https://pillow.readthedocs.io/en/3.1.x/reference/Image.html
    # Credit: https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_core/py_basic_ops/py_basic_ops.html

    filename = os.path.expanduser(filename)

    r_dict = dict()
    if '.gif' in filename:
        im = Image.open(filename)
        rgb_im = im.convert('RGB')
        rgb_im.save('tmp.jpg')
        img = cv2.imread('tmp.jpg')
        h, w = img.shape[:2]



        r_dict['w'] = w
        r_dict['h'] = h
        os.remove('tmp.jpg')
    else:
        img = cv2.imread(filename)
        h, w = img.shape[:2]

        r_dict['w'] = w
        r_dict['h'] = h

    FACE_DATA_PATH = '/home/ecegridfs/a/ee364/site-packages/cv2/data/haarcascade_frontalface_default.xml'
    haar_face_cascade = cv2.CascadeClassifier(FACE_DATA_PATH)

    img_gry = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = haar_face_cascade.detectMultiScale(img_gry, 1.3, 5)
    faces_list = list()


    for face in faces:
        faces_t_dict = dict()
        faces_t_dict['w'] = face[2]
        faces_t_dict['h'] = face[3]

        faces_t_dict['x'] = face[0]
        faces_t_dict['y'] = face[1]
        faces_list.append(faces_t_dict)

    faces_list.sort(key=lambda x: int(x['h']) * int(x['w']), reverse=True)
    r_dict['faces'] = faces_list

    return r_dict


def find_profile_photo_filename(filename_to_etree):

    for key in filename_to_etree:
        img_info = get_image_info(key)
        if img_info['faces'] is not None:
            if len(img_info['faces']) == 1:
                if (img_info['w']* img_info['h'])/(img_info['faces'][0]['w']*img_info['faces'][0]['h']) > 0.40:
                    # find_profile_photo_htmlElement(value)
                    return key

# def find_profile_photo_htmlElement(value):
#     print(value)
#     return value

def add_glasses(filename, face_info, color):
    # face_info is a dict like {"w":w, "h":h, "x":x, "y":y}
    f_xl = face_info['x']                   # left most boundary of face in pic
    f_xr = face_info['x']+face_info['w']    # right most boundary of face in pic
    f_y = face_info['y']
    f_w = face_info['w']
    f_h = face_info['h']

    filename = os.path.expanduser(filename)
    from PIL import Image
    import numpy as np
    if '.gif' in filename:
        im = Image.open(filename)
        rgb_im = im.convert('RGB')
        rgb_im.save('tmp.jpg')
        img = cv2.imread('tmp.jpg')


        os.remove('tmp.jpg')
    else:
        img = cv2.imread(filename)


    img_gry = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    EYE_DATA_PATH = '/home/ecegridfs/a/ee364/site-packages/cv2/data/haarcascade_eye.xml'
    haar_eye_cascade = cv2.CascadeClassifier(EYE_DATA_PATH)

    eyes = haar_eye_cascade.detectMultiScale(img_gry, 1.3, 5)
    # print(eyes)
    if len(eyes) == 1:

        if eyes[0][0] - f_xl < f_xr - eyes[0][0]:   # we have left hand eye (right eye)
            new_eye_x = f_w//2+f_xl

        else:                                       # we have right hand eye (left eye)

            new_eye_x = f_w//2

        eyes = np.append(eyes, [[new_eye_x, eyes[0][1], eyes[0][2], eyes[0][3]]], axis=0 )

    elif len(eyes) == 0 or len(eyes) > 2:

        e_w = f_w//7
        e_h = f_h//7
        e_xl = f_w//2 + f_xl - e_w//2 - e_w
        e_xr = f_w//2 + f_xl + e_w//2

        # e_xr = e_xl + e_w + e_w
        e_y = f_h//3 + f_y


        eyes = list()
        eyes.append([e_xl, e_y, e_w, e_h])
        eyes.append([e_xr, e_y, e_w, e_h])
    elif len(eyes) == 2:
        if eyes[0,2] < eyes[1,2]:
            eyes[1,2] = eyes[0,2]
        else:
            eyes[0,2] = eyes[1,2]

        if eyes[0,3] > eyes[1,3]:
            eyes[1,3] = eyes[0,3]
        else:
            eyes[0,3] = eyes[1,3]

        if eyes[0,1] < eyes[1,1]:
            eyes[0,1] = eyes[1,1]
        else:
            eyes[1,1] = eyes[0,1]





    glasses_frame_color_rgb = dict()

    glasses_frame_color_rgb['black'] = (0,0,0)
    glasses_frame_color_rgb['red'] = (0,0,255)
    glasses_frame_color_rgb['green'] = (0,255,0)
    glasses_frame_color_rgb['blue'] = (255,0,0)
    glasses_frame_color_rgb['white'] = (255,255,255)

    if f_w < 100:
        thick = 1
    elif f_w < 250:
        thick = 2
    elif f_w < 350:
        thick = 3
    elif f_w < 450:
        thick = 4
    elif f_w >= 450:
        thick = 5

    # print(thick)


    # x y w h
    for eye in eyes:

        e_x = eye[0]
        e_y = eye[1]
        e_w = eye[2]
        e_h = eye[3]

        cv2.rectangle(img,(e_x,e_y),(e_x+e_w, e_y+e_h), glasses_frame_color_rgb[color], thick)
        if e_x - f_xl < f_xr - (e_x+e_w):
            cv2.line(img, (e_x, e_y+e_h//2), (f_xl, e_y), glasses_frame_color_rgb[color], thick)
            le_x = e_x
        else:
            cv2.line(img, (e_x+e_w, e_y+e_h//2), (f_xr, e_y), glasses_frame_color_rgb[color], thick)
            re_x = e_x

    cv2.line(img, (le_x+e_w, e_y+e_h//2), (re_x, e_y+e_h//2), glasses_frame_color_rgb[color], thick)
    cv2.imwrite(filename, img)


def copy_profile_photo_to_static(etree):

    with fetch_images(etree) as filename_to_node:
        name = find_profile_photo_filename(filename_to_node)   # returns filename
        static_dir = os.path.join(sys.path[0], "static")

        shutil.copy(name, static_dir)

    # print(filename_to_node[name])

    abs_path_file = os.path.join(static_dir, name)

    return os.path.abspath(abs_path_file)

def _profile_photo_htmlElement(etree):
    with fetch_images(etree) as filename_to_node:
        name = find_profile_photo_filename(filename_to_node)   # returns filename

    # print(filename_to_node[name])
    return filename_to_node[name]


def make_filename(url, extension):
    converted = hashlib.sha1(url).hexdigest()
    filename = '{}{}'.format(converted, extension)

    return filename



def get_html_at_url(url, charset="UTF-8"):

    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'PurdueUniversityClassProject/1.0 (jung199@purdue.edu https://goo.gl/dk8u5S)')
    # Credit: Adapted from example in Python 3.4 Documentation, urllib.request
    # License: PSFL https://www.python.org/download/releases/3.4.1/license/
    #          https://docs.python.org/3.4/library/urllib.request.html


    connect = urllib.request.urlopen(req)
    html_str = connect.read().decode("utf8")
    # Credit:  https://docs.python.org/3/library/urllib.request.html

    return html_str


def _make_etree(html, url):
    from lxml.html import HTMLParser, document_fromstring

    parser = HTMLParser(encoding="UTF-8")
    root = document_fromstring(html, parser=parser, base_url=url)
    root.make_links_absolute(root.base_url)

    return root


def add_base_tag_html_str(html, url):
    base_tag = '<base target="_self" href="{}">'.format(url)
    html_str_w_base = str(html).replace('<head>', '<head>' + '\n' + base_tag)
    return html_str_w_base


app = flask.Flask(__name__)
@app.route('/')
def root_page():
    return flask.render_template('root.html')


@app.route('/view')
def view_page():
    import lxml
    value = flask.request.args.get("url")
    color = flask.request.args.get("color")



    if re.search(r'^(http:\/\/www\.|https:\/\/www\.|http:\/\/|https:\/\/)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$', value) is not None:
        if re.search(r'(?:facebook\.|fb\.|instagram\.|whatsapp\.|qq\.|wechat\.|tumblr\.|twitter\.|baidu\.|skype\.|snapchat\.|line\.|vk\.|pinterest\.|reddit\.|myspace\.|youtube\.)', value) is None:


            # print(color)



            html_str = get_html_at_url(value)
            html = add_base_tag_html_str(html_str, value)
            etree = _make_etree(html, value)




            abs_path = copy_profile_photo_to_static(etree)      # absolute path for modified image
            html_el = _profile_photo_htmlElement(etree)         # html element for profile picture




            im_info = get_image_info(abs_path)
            add_glasses(abs_path, im_info['faces'][0], color)

            # creates online url for modified image
            static_url = flask.url_for('static', filename=os.path.basename(abs_path), _external=True)


            html_el.set("src", static_url)



            return lxml.html.tostring(etree)
        else:
            flask.flash("No! You can't do SNS. That's just too naughty.")
            return flask.redirect(flask.url_for('root_page'))
            # return "No! You can't do SNS. That's just too naughty."
    else:
        flask.flash('Invalid url form. Maybe you left it empty or forgot http://?')
        return flask.redirect(flask.url_for('root_page'))

if __name__ == '__main__':
    app.secret_key = b'alexqthegodsent'
    app.run(host="127.0.0.1", port=os.environ.get("ECE364_HTTP_PORT", 10211),
            use_reloader=True, use_evalex=False, debug=True, use_debugger=False)


    # Credit:  Alex Quinn.  Used with permission.  Preceding line only.
