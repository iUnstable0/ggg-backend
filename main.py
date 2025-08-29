import os
from io import BytesIO
import random
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename

from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageOps, ImageEnhance

UPLOAD_FOLDER = './files'
ALLOWED_TYPES = ['png', 'jpeg', 'heif', 'heic']

EMOJI_DIR = "./emojis"


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def ghostify(im: Image.Image, ghostpacify, ghostshit) -> Image.Image:
    im = im.convert("RGBA")

    opacity = max(0.0, min(1.0, ghostpacify))
    w, h = im.size

    dx = random.randint(-abs(ghostshit), abs(ghostshit))
    dy = random.randint(-abs(ghostshit), abs(ghostshit))

    ghost = im.copy()
    ghost.putalpha(int(opacity * 255))

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    layer.paste(ghost, (dx, dy), ghost)

    return (Image.alpha_composite(im, layer)).convert('RGB')

def deep_fry(im: Image.Image, loops, quality, subsample, posterizebits) -> Image.Image:
    im = im.convert("RGB")

    ## low res ###############

    w, h = im.size

    im = im.resize((max(1, w // 4), max(1, h // 4)), resample=Image.BOX)

    ## make it look rlly stretched ###############

    w, h = im.size

    w_scale = 1.1
    h_scale = 0.8

    new_size = (max(1, int(w * w_scale)), max(1, int(h * h_scale)))

    im = im.resize(new_size, resample=Image.BOX)


    ## make color tiktok ###############

    if posterizebits:
        im = ImageOps.posterize(im, bits=3)

    ##############################################

    # im = ImageEnhance.Color(im).enhance(color)
    # im = ImageEnhance.Contrast(im).enhance(contrast)
    # im = ImageEnhance.Brightness(im).enhance(brightness)

    for _ in range(loops):
        buf = BytesIO()
        im.save(buf, "JPEG", quality=quality, subsampling=subsample, optimize=False, progressive=True)
        buf.seek(0)
        im = Image.open(buf).convert("RGB")

    return im

def draw_text(im: Image.Image, text: str, font: str, size: int, xy=(0, 0),fill=(255, 255, 255, 255), max_width=None) -> Image.Image:
    im = im.convert("RGBA")

    draw = ImageDraw.Draw(im)
    x0, y0 = xy
    x, y = xy

    font = ImageFont.truetype(font, size)

    ascent, descent = font.getmetrics()
    line_h = int(ascent + descent) * 1.1
    emoji_h = 1

    index=0
    emojipos = []

    draw = ImageDraw.Draw(im)

    for part in text.split(":"):
        if part.strip() == "":
            index += 1
            continue

        if part+".png" in os.listdir(EMOJI_DIR):
            emojipos.append(index)
            print("Emoji: " + part)

            emoji = Image.open(os.path.join(EMOJI_DIR, part+".png")).convert("RGBA")
            eh = emoji.size[1]
            ew = emoji.size[0]
            emoji = emoji.resize((int(ew * (emoji_h / eh)), emoji_h), resample=Image.LANCZOS)

            if max_width and x + emoji.size[0] > x0 + max_width:
                x = x0
                y += line_h

            im.paste(emoji, (x, y), emoji)
            x += emoji.size[0]
        else:
            draw.text((x, y), part, fill=fill, font=font)
            x += draw.textlength(part, font=font)
            print(part)

        index += 1


    return im.convert("RGB")

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

# def allowed_file(filename: str) -> bool:
#     if '.' not in filename:
#         return False
#     ext = filename.rsplit('.', 1)[1].lower()
#     return ext in ALLOWED_TYPES

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return {"error": "No file part in request (expect key 'file')"}, 400

    file = request.files['file']

    if file.filename == '':
        return {"error": "No selected file"}, 400

    mimetype = file.content_type

    print(mimetype)

    if mimetype.split('/')[1] not in ALLOWED_TYPES:
        return {"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES)}"}, 400
    else:
        print("supported")

    quality = request.form.get('quality', default=20, type=int)
    loops = request.form.get('loops', default=3, type=int)
    subsample = request.form.get('subsample', default=2, type=int)
    posterizebits = request.form.get('posterizebits', default="true", type=str).lower() == "true"
    brightness = request.form.get('brightness', default=1, type=float)
    ghost = request.form.get('ghost', default="true", type=str).lower() == "true"
    ghostpacify = request.form.get('ghostpacify', default=0.5, type=float)
    ghostshit = request.form.get('ghostshit', default=10, type=int)

    r = int(request.form.get('r', default=255, type=int))
    g = int(request.form.get('g', default=255, type=int))
    b = int(request.form.get('b', default=255, type=int))
    alpha = int(request.form.get('alpha', default=255, type=int))

    message = request.form.get('message', default="Hello,  My Goat ❤️", type=str)

    print(quality, loops, subsample, posterizebits)
    # return {"error": "Testing"}, 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)


    with Image.open(save_path) as im:
        im = ImageEnhance.Brightness(im).enhance(brightness)

        # font = ImageFont.truetype("./fonts/papyrus.ttf", im.size[1] // 8)

        # draw = ImageDraw.Draw(im)
        # draw.text((1,1), "Hello,  My Goat", font=font, fill=(r,g,b, alpha))

        im = draw_text(im, message, "./fonts/papyrus.ttf", im.size[1] // 8)
        im = deep_fry(im, loops=loops, quality=quality, subsample=subsample, posterizebits=posterizebits)
        im = ghostify(im, ghostpacify=ghostpacify, ghostshit=ghostshit)

        im.save(save_path,     "JPEG")

    return {"ok": True, "filename": filename, "path": save_path}, 201
