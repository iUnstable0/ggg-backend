import os
from io import BytesIO
import random
import shutil
# from flask import Flask, flash, request, redirect, url_for, make_response
from pathlib import Path
from typing import Union, Annotated, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid

from werkzeug.utils import secure_filename

from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageOps, ImageEnhance
import pillow_heif

pillow_heif.register_heif_opener()

UPLOAD_FOLDER = Path("./files")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = ['png', 'jpeg', 'heif', 'heic']

EMOJI_DIR = "./emojis"

fonts = ["./fonts/papyrus.ttf", "./fonts/comic-sans.ttf", "./fonts/fancy.ttf", "./fonts/roboto.ttf"]
# app = Flask(__name__)
origins = [
    "http://localhost:3000"
]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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


def draw_text(im: Image.Image, text: str, font: int, size: int, xy=(0, 0), fill=(255, 255, 255, 255),
              max_width=None) -> Image.Image:
	im = im.convert("RGBA")

	draw = ImageDraw.Draw(im)
	x0, y0 = xy
	x, y = xy

	font = fonts[font - 1]

	font = ImageFont.truetype(font, size)

	ascent, descent = font.getmetrics()
	line_h = int((ascent + descent) * 1.1)
	emoji_h = int(ascent)

	max_width = im.size[0]

	index = 0
	emojipos = []

	draw = ImageDraw.Draw(im)

	for part in text.split(":"):
		if part.strip() == "":
			index += 1
			continue

		if part + ".png" in os.listdir(EMOJI_DIR):
			emojipos.append(index)
			print("Emoji: " + part)

			emoji = Image.open(os.path.join(EMOJI_DIR, part + ".png")).convert("RGBA")
			eh = emoji.size[1]
			ew = emoji.size[0]

			new_w = max(1, int(ew * (emoji_h / eh)))
			new_h = max(1, int(emoji_h))

			emoji = emoji.resize((new_w, new_h), resample=Image.LANCZOS)

			# im.paste(emoji, (x, y), emoji)
			# im.paste(emoji, (int(x), int(y)), emoji)
			im.paste(emoji, (int(x), int(y)), emoji)
			x += emoji.size[0]
		else:
			length = int(draw.textlength(part, font=font))
			print(f"Text: {part} length={length} x={x} y={y}")

			if length > max_width:
				for char in part:
					print(char)
					char_length = int(draw.textlength(char, font=font))
					if max_width and x + char_length > x0 + max_width:
						print(f"Character too long: {char} x={x0} y={y}")
						x = x0
						y += line_h
					# draw.text((x, y), char, fill=fill, font=font)
					draw.text((int(x), int(y)), char, fill=fill, font=font)
					x += char_length
			else:
				# draw.text((x, y), part, fill=fill, font=font)
				draw.text((int(x), int(y)), part, fill=fill, font=font)  # be safe
				x += draw.textlength(part, font=font)

			print(part)

		index += 1

	return im.convert("RGB")


@app.get("/")
def hello_world():
	return JSONResponse(status_code=200, content={"hello": "world"})


# def allowed_file(filename: str) -> bool:
#     if '.' not in filename:
#         return False
#     ext = filename.rsplit('.', 1)[1].lower()
#     return ext in ALLOWED_TYPES


@app.post('/upload')
def upload_file(
		file: UploadFile,
		quality: int = Form(20),
		loops: int = Form(3),
		subsample: int = Form(2),
		posterizebits: bool = Form(True),
		brightness: float = Form(1.0),
		contrast: float = Form(1.0),
		ghost: bool = Form(True),
		ghostpacify: float = Form(0.5),
		ghostshit: int = Form(10),
		font: int = Form(1),
		r: int = Form(255),
		g: int = Form(255),
		b: int = Form(255),
		alpha: int = Form(255),
		message: str = Form("Hello,  My Goat ❤️")
):
	mimetype = file.content_type

	print(mimetype)

	if mimetype.split('/')[1] not in ALLOWED_TYPES:
		raise HTTPException(status_code=400, detail="Unsupported file type")
		# return {"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES)}"}, 400
	else:
		print("supported")

	# quality = request.form.get('quality', default=20, type=int)
	# loops = request.form.get('loops', default=3, type=int)
	# subsample = request.form.get('subsample', default=2, type=int)
	#
	# posterizebits = request.form.get('posterizebits', default="true", type=str).lower() == "true"
	#
	# brightness = request.form.get('brightness', default=1, type=float)
	# contrast = request.form.get('contrast', default=1, type=float)
	#
	# ghost = request.form.get('ghost', default="true", type=str).lower() == "true"
	# ghostpacify = request.form.get('ghostpacify', default=0.5, type=float)
	# ghostshit = request.form.get('ghostshit', default=10, type=int)
	#
	# font = request.form.get('font', default=1, type=int)
	#
	# r = int(request.form.get('r', default=255, type=int))
	# g = int(request.form.get('g', default=255, type=int))
	# b = int(request.form.get('b', default=255, type=int))
	# alpha = int(request.form.get('alpha', default=255, type=int))
	#
	# message = request.form.get('message', default="Hello,  My Goat ❤️", type=str)

	# print(quality, loops, subsample, posterizebits)
	# return {"error": "Testing"}, 400

	print(file.filename)

	filename = f"{file.filename.split(".").pop(0)}-{uuid.uuid4()}"
	extension = f".{file.filename.split(".").pop()}"
	savename = secure_filename(filename)

	in_path = UPLOAD_FOLDER / f"{filename}.temp"
	out_path = UPLOAD_FOLDER / f"{filename}.jpg"

	with in_path.open("wb") as out:
		shutil.copyfileobj(file.file, out)

	try:
		with Image.open(in_path) as im:
			im = ImageEnhance.Brightness(im).enhance(brightness)
			im = ImageEnhance.Contrast(im).enhance(contrast)

			# font = ImageFont.truetype("./fonts/papyrus.ttf", im.size[1] // 8)

			# draw = ImageDraw.Draw(im)
			# draw.text((1,1), "Hello,  My Goat", font=font, fill=(r,g,b, alpha))

			im = draw_text(im, message, font, im.size[1] // 8, fill=(r, g, b, alpha))
			im = deep_fry(im, loops=loops, quality=quality, subsample=subsample, posterizebits=posterizebits)

			if ghost:
				im = ghostify(im, ghostpacify=ghostpacify, ghostshit=ghostshit)

			im.convert("RGB").save(out_path, "JPEG")
	except Exception as e:
		print(e)
		raise HTTPException(status_code=500, detail="Failed to process image")
	finally:
		try:
			in_path.unlink(missing_ok=True)
		except:
			pass

	return JSONResponse(status_code=201, content={"ok": True, "filename": out_path.name})
