import os
from io import BytesIO
import random
import shutil
import schedule
import time
# from flask import Flask, flash, request, redirect, url_for, make_response
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
import threading
import uuid

from werkzeug.utils import secure_filename

from PIL import Image, ImageFont, ImageDraw, ImageFilter, ImageOps, ImageEnhance
import pillow_heif

pillow_heif.register_heif_opener()

UPLOAD_FOLDER = Path("./files")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGES_TYPES = ['png', 'jpeg', 'heif', 'heic']
ALLOWED_VIDEO_TYPES = ['mp4', 'mov', 'webm', 'avi', "quicktime"]

EMOJI_DIR = "./emojis"

fonts = ["./fonts/papyrus.ttf", "./fonts/comic-sans.ttf", "./fonts/fancy.ttf", "./fonts/roboto.ttf"]
# app = Flask(__name__)
origins = [
	"http://localhost:3000",
	"https://ggg.iustb0.fun"
]


def cleanup():
	# print("cleaning files")

	now = time.time()

	try :
		for file in UPLOAD_FOLDER.iterdir():
			if file.is_file() and file.name != "dot":
				try:
					modifiedTime = file.stat().st_mtime
					age = now - modifiedTime

					#5 mins
					if age > 300:
						print(f"Deleting old file: {file.name}")
						file.unlink(missing_ok=True)
				except Exception as e:
					print(e)
	except Exception as e:
		print(e)

	# print("cleanup done")


def scheduler():
	cleanup()

	schedule.every(1).minutes.do(cleanup)

	while True:
		schedule.run_pending()
		time.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
	print("Starting app")

	scheduler_thread = threading.Thread(target=scheduler, daemon=True)
	scheduler_thread.start()

	yield
	print("Exiting!")
app = FastAPI(lifespan=lifespan)

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

	# w, h = im.size
	#
	# im = im.resize((max(1, w // 2), max(1, h // 2)), resample=Image.BOX)


	w, h = im.size

	w_scale = 1.1
	h_scale = 0.8

	new_size = (max(1, int(w * w_scale)), max(1, int(h * h_scale)))

	im = im.resize(new_size, resample=Image.BOX)

	## make color tiktok ###############

	if posterizebits:
		im = ImageOps.posterize(im, bits=3)

	for _ in range(loops):
		buf = BytesIO()
		im.save(buf, "JPEG", quality=quality, subsampling=subsample, optimize=False, progressive=True)
		buf.seek(0)
		im = Image.open(buf).convert("RGB")

	return im

def draw_text(im: Image.Image, text: str, font: int, size: int, fill=(255, 255, 255, 255),
              max_width=None, squishText=False, textPlacement: str = "topleft", margin: int = 10, emojiGlows=False) -> Image.Image:

	im = im.convert("RGBA")

	draw = ImageDraw.Draw(im)
	img_w, img_h = im.size

	if max_width is None:
		max_width = img_w - (margin * 2)

	font_path = fonts[font - 1]

	min_size = int(size * 0.5)

	final_size = size
	font_obj = ImageFont.truetype(font_path, final_size)

	if squishText:
		for current_size in range(size, min_size - 1, -1):
			font_obj = ImageFont.truetype(font_path, current_size)
			ascent, _ = font_obj.getmetrics()
			emoji_h = int(ascent)

			total_width = 0

			for part in text.split(":"):
				if part.strip() and part + ".png" in os.listdir(EMOJI_DIR):
					emoji = Image.open(os.path.join(EMOJI_DIR, part + ".png"))
					eh, ew = emoji.size
					new_w = max(1, int(ew * (emoji_h / eh)))
					total_width += new_w
				else:
					total_width += draw.textlength(part, font=font_obj)
			
			if total_width <= max_width:
				final_size = current_size
				break
		else:
			final_size = min_size

	font_obj = ImageFont.truetype(font_path, final_size)
	ascent, descent = font_obj.getmetrics()

	line_h = int((ascent + descent) * 1.1)
	emoji_h = int(ascent)
	space_width = draw.textlength(" ", font=font_obj)

	words = []

	for part in text.split(":"):
		if part.strip() and part + ".png" in os.listdir(EMOJI_DIR):
			words.append(f":{part}:")
		else:
			words.extend(part.split())

	current_x = 0
	current_y = 0
	max_line_width = 0

	for word in words:
		is_emoji = word.startswith(":") and word.endswith(":") and word[1:-1] + ".png" in os.listdir(EMOJI_DIR)
        
		word_width = 0
		if is_emoji:
			emoji_name = word[1:-1]
			emoji = Image.open(os.path.join(EMOJI_DIR, emoji_name + ".png"))
			eh, ew = emoji.size
			word_width = max(1, int(ew * (emoji_h / eh)))
		else:
			word_width = draw.textlength(word, font=font_obj)
		
		if current_x + word_width > max_width:
			max_line_width = max(max_line_width, current_x)
			current_x = 0
			current_y += line_h
		
		current_x += word_width + space_width
	
	max_line_width = max(max_line_width, current_x - space_width)
	text_block_width = max_line_width
	text_block_height = current_y + line_h

	start_x, start_y = 0, 0
	if textPlacement == "topleft":
		start_x, start_y = margin, margin
	elif textPlacement == "topright":
		start_x, start_y = img_w - text_block_width - margin, margin
	elif textPlacement == "bottomleft":
		start_x, start_y = margin, img_h - text_block_height - margin
	elif textPlacement == "bottomright":
		start_x, start_y = img_w - text_block_width - margin, img_h - text_block_height - margin
	elif textPlacement == "center":
		start_x = (img_w - text_block_width) / 2
		start_y = (img_h - text_block_height) / 2
	
	x, y = start_x, start_y

	for word in words:
		is_emoji = word.startswith(":") and word.endswith(":") and word[1:-1] + ".png" in os.listdir(EMOJI_DIR)

		if is_emoji:
			emoji_name = word[1:-1]
			emoji_obj = Image.open(os.path.join(EMOJI_DIR, emoji_name + ".png")).convert("RGBA")

			eh, ew = emoji_obj.size
			new_w = max(1, int(ew * (emoji_h/ eh)))
			new_h = max(1, int(emoji_h))
			emoji = emoji_obj.resize((new_w, new_h), resample=Image.LANCZOS)

			if emojiGlows:
				emoji = ImageEnhance.Brightness(emoji).enhance(2)
				emoji = emoji.filter(ImageFilter.GaussianBlur(radius=2))

			final_emoji_to_paste = emoji
			word_width = new_w

			if emojiGlows:
				glow_size = (int(new_w * 1.5), int(new_h * 1.5))
				glow_layer = emoji_obj.resize(glow_size, resample=Image.LANCZOS)
				glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=15))
				glow_layer = ImageEnhance.Brightness(glow_layer).enhance(10)

				canvas = Image.new('RGBA', glow_size, (0, 0, 0, 0))

				canvas.paste(glow_layer, (0, 0), glow_layer)

				offset_x = (glow_size[0] - new_w) // 2
				offset_y = (glow_size[1] - new_h) // 2

				canvas.paste(emoji, (offset_x, offset_y), emoji)

				final_emoji_to_paste = canvas
				word_width = glow_size[0]

			if x + word_width > start_x + max_width:
				x = start_x
				y += line_h
			
			im.paste(final_emoji_to_paste, (int(x), int(y)), final_emoji_to_paste)
			x += word_width + space_width
		else:
			word_width = draw.textlength(word, font=font_obj)
			if x + word_width > start_x + max_width:
				x = start_x
				y += line_h
			
			draw.text((int(x), int(y)), word, fill=fill, font=font_obj)
			x += word_width + space_width
	
	return im.convert("RGB")

@app.get("/")
def hello_world():
	return JSONResponse(status_code=200, content={"hello": "world"})


app.mount("/files", StaticFiles(directory="files"), name="files")


class File(BaseModel):
	name: str


@app.post("/delete")
def delete_file(
		file: File
):


	name = secure_filename(file.name)
	path = UPLOAD_FOLDER / name

	print(path.exists())

	if not path.exists():
		raise HTTPException(status_code=400, detail="File not found")

	try:
		path.unlink(missing_ok=True)
	except:
		pass

	return JSONResponse(status_code=200, content={
		"ok": True
	})

def opposite_text_placement(textPlacement: str) -> str:
	if textPlacement == "topleft":
		return "bottomleft"
	elif textPlacement == "topright":
		return "bottomleft"
	elif textPlacement == "bottomleft":
		return "topleft"
	elif textPlacement == "bottomright":
		return "topleft"

@app.post("/upload-video")
def upload_video(
		file: UploadFile,
		madeWithPrincessMode: bool = Form(False),
		squishText: bool = Form(False),
		quality: int = Form(20),
		loops: int = Form(3),
		subsample: int = Form(2),
		posterizebits: bool = Form(True),
		brightness: float = Form(1.0),
		contrast: float = Form(1.0),
		ghost: bool = Form(True),
		ghostpacify: float = Form(0.5),
		ghostshit: int = Form(10),
		fps: int = Form(10),
		font: int = Form(1),
		textPlacement: str = Form("topleft"),
		emojiGlows: bool = Form(False),
		r: int = Form(255),
		g: int = Form(255),
		b: int = Form(255),
		alpha: int = Form(255),
		message: str = Form("Hello,  My Goat ❤️")
):
	mimetype = file.content_type

	print(mimetype)

	if not mimetype.startswith("video/"):
		raise HTTPException(status_code=400, detail="Unsupported file type")

	if mimetype.split('/')[1] not in ALLOWED_VIDEO_TYPES:
		raise HTTPException(status_code=400, detail="Unsupported file type")
	else:
		print("supported")

	filename = uuid.uuid4()

	in_path = UPLOAD_FOLDER / f"{filename}.temp"
	out_path = UPLOAD_FOLDER / f"{filename}.gif"

	with in_path.open("wb") as out:
		shutil.copyfileobj(file.file, out)

	processed_frames = []
	clip = None

	try:
		clip = VideoFileClip(str(in_path))

		for frame in clip.iter_frames(fps=fps, dtype="uint8"):
			max_width = 480

			im = Image.fromarray(frame)

			w, h = im.size

			if w > max_width:
				new_h = int(h * (max_width / w))
				im = im.resize((max_width, new_h), resample=Image.LANCZOS)

			im = ImageEnhance.Brightness(im).enhance(brightness)
			im = ImageEnhance.Contrast(im).enhance(contrast)

			im = draw_text(im, message, font, im.size[1] // 8, fill=(r, g, b, alpha), squishText=squishText, textPlacement=textPlacement, emojiGlows=emojiGlows)

			if madeWithPrincessMode:
				im = draw_text(im, "Made in princess mode :sparkling-heart:", font, im.size[1] // 16, fill=(r, g, b, alpha), xy=(50, im.size[1] - 100), squishText=squishText, textPlacement=opposite_text_placement(textPlacement), emojiGlows=emojiGlows)

			im = deep_fry(im, loops=loops, quality=quality, subsample=subsample, posterizebits=posterizebits)

			if ghost:
				im = ghostify(im, ghostpacify=ghostpacify, ghostshit=ghostshit)

			processed_frames.append(im)

		if not processed_frames:
			raise HTTPException(status_code=500, detail="Failed to process video no frames")

		duration_ms = int(1000 / fps)
		processed_frames[0].save(
			out_path,
			save_all=True,
			append_images=processed_frames[1:],
			duration=duration_ms,
			loop=0
		)

	except Exception as e:
		print(e)
		raise HTTPException(status_code=500, detail="Failed to process video")
	finally:
		if clip:
			clip.close()
		try:
			in_path.unlink(missing_ok=True)
		except:
			pass

	return JSONResponse(status_code=201, content={"ok": True, "filename": out_path.name})
@app.post('/upload')
def upload_image(
		file: UploadFile,
		madeWithPrincessMode: bool = Form(False),
		squishText: bool = Form(False),
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
		textPlacement: str = Form("topleft"),
		emojiGlows: bool = Form(False),
		r: int = Form(255),
		g: int = Form(255),
		b: int = Form(255),
		alpha: int = Form(255),
		message: str = Form("Hello,  My Goat ❤️")
):
	mimetype = file.content_type

	print(mimetype)


	if not mimetype.startswith("image/"):
		raise HTTPException(status_code=400, detail="Unsupported file type")

	if mimetype.split('/')[1] not in ALLOWED_IMAGES_TYPES:
		raise HTTPException(status_code=400, detail="Unsupported file type")

	else:
		print("supported")

	print(file.filename)

	name = secure_filename(file.filename)

	# filename = f"{name.split(".").pop(0)}-{uuid.uuid4()}"
	filename = uuid.uuid4()

	in_path = UPLOAD_FOLDER / f"{filename}.temp"
	out_path = UPLOAD_FOLDER / f"{filename}.jpg"

	with in_path.open("wb") as out:
		shutil.copyfileobj(file.file, out)

	try:
		with Image.open(in_path) as im:
			im = ImageOps.exif_transpose(im)

			im = ImageEnhance.Brightness(im).enhance(brightness)
			im = ImageEnhance.Contrast(im).enhance(contrast)

			im = draw_text(im, message, font, im.size[1] // 8, fill=(r, g, b, alpha), squishText=squishText, textPlacement=textPlacement, emojiGlows=emojiGlows)

			if madeWithPrincessMode:
				im = draw_text(im, "Made in princess mode :sparkling-heart:", font, im.size[1] // 16, fill=(r, g, b, alpha), xy=(50, im.size[1] - 150), squishText=squishText, textPlacement=opposite_text_placement(textPlacement), emojiGlows=emojiGlows)

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