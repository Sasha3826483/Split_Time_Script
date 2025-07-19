import os
import re
import math
import datetime
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import shutil

# тест новой ветки гита
# Еще один комментарий для теста новой ветки
# Тестовый коммент для ветки 2
# Текстовый коммент для нового коммита
# Еще коммент

# === Настройки путей и Tesseract ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
today_str = datetime.date.today().strftime("%d.%m.%Y")
INPUT_FOLDER = r"C:\images"
OUTPUT_FOLDER = "output"
RESULT_FOLDER = os.path.join("results", f"{today_str}")
CROPPED_AREA = (220, 0, 1500, 100)  # Область, где находятся два времени
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# === Шрифты ===
try:
    FONT_TEXT = ImageFont.truetype("arial.ttf", size=24)
    FONT_TEXT_FOR_BACKGROUND = ImageFont.truetype("arial.ttf", size=40)
    FONT_LABEL = ImageFont.truetype("arial.ttf", 50)
except:
    FONT_TEXT = FONT_LABEL = ImageFont.load_default()

# === Регулярка и парсинг времени ===
TIME_REGEX = r'\d{1,2}:\d{2}:\d{2}'

def extract_times(text):
    return re.findall(TIME_REGEX, text)

def to_milliseconds(time_str):
    m, s, cs = map(int, time_str.split(":"))
    return (m * 60 + s) * 1000 + cs * 10

def format_ms(ms):
    mm = ms // 60000
    ss = (ms % 60000) // 1000
    mss = ms % 1000
    return f"{ss:02}:{mss:03}"

def draw_text_with_background(draw, position, text, font, text_color=(255, 0, 0), bg_color=(255, 255, 255), padding=6):
    bbox = draw.textbbox(position, text, font=font)
    x0, y0, x1, y1 = bbox
    draw.rectangle((x0 - padding, y0 - padding, x1 + padding, y1 + padding), fill=bg_color)
    draw.text(position, text, font=font, fill=text_color)

# === Обработка изображений и OCR ===

if os.path.exists(OUTPUT_FOLDER):   # Предварительно очистим содержимое каталога с обработанными файлами. Если каталога нет, то создадим новый
    for f in os.listdir(OUTPUT_FOLDER):
        path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(path):
            os.unlink(path)         # удаляет файл
        elif os.path.isdir(path):
            shutil.rmtree(path)     # удаляет подпапку и всё в ней
else:
    os.makedirs(OUTPUT_FOLDER)


def process_image(img_path):
    img = Image.open(img_path)
    cropped = img.crop(CROPPED_AREA)

    ocr_text = pytesseract.image_to_string(
        cropped, config='--psm 6 -c tessedit_char_whitelist=0123456789:'
    )
    times = extract_times(ocr_text)

    if len(times) >= 2:
        try:
            diff = abs(to_milliseconds(times[1]) - to_milliseconds(times[0]))
            result_text = f"dt={format_ms(diff)}s"
        except Exception as e:
            result_text = f"Ошибка: {e}"
    else:
        result_text = "Не удалось найти два времени"

    draw = ImageDraw.Draw(img)
    draw_text_with_background(draw, (300, CROPPED_AREA[3] + 10), result_text, FONT_TEXT_FOR_BACKGROUND)

    out_name = os.path.join(OUTPUT_FOLDER, os.path.basename(img_path))
    img.save(out_name)
    print(f"[OK] {os.path.basename(img_path)}: {times} -> {result_text}")

# === Обработка всех PNG-файлов ===
for file in os.listdir(INPUT_FOLDER):
    if file.lower().endswith(".png"):
        process_image(os.path.join(INPUT_FOLDER, file))

# === Пользовательский ввод для шапки ===
label_text1 = f"Проверка - {input('Проверка: ')}"
label_text2 = f"Номер агрегата - {input('Номер агрегата: ')}"
label_text3 = f"Оператор - {input('Оператор: ')}"

# === Генерация страниц A4 ===
INPUT_FOLDER = r"output"
A4_WIDTH_PX = 3508
A4_HEIGHT_PX = 2480
DPI = 300
HEADER_HEIGHT = 150
ROWS, COLS = 2, 2
IMAGES_PER_PAGE = ROWS * COLS
CELL_WIDTH = A4_WIDTH_PX // COLS
CELL_HEIGHT = (A4_HEIGHT_PX - HEADER_HEIGHT) // ROWS

try:
    caption_font = ImageFont.truetype("arial.ttf", 50)
except:
    caption_font = ImageFont.load_default()

all_files = sorted([
    f for f in os.listdir(INPUT_FOLDER)
    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
])
all_images = [Image.open(os.path.join(INPUT_FOLDER, f)).convert("RGB") for f in all_files]
total_pages = math.ceil(len(all_images) / IMAGES_PER_PAGE)

for page_num in range(total_pages):
    result = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), (255, 255, 255))
    draw = ImageDraw.Draw(result)

    # === Шапка ===
    draw.text((50, 50), today_str, font=FONT_LABEL, fill=(0, 0, 0))
    page_label = f"Стр. {page_num + 1}"
    label_width = FONT_LABEL.getbbox(page_label)[2]
    draw.text((A4_WIDTH_PX - label_width - 50, 50), page_label, font=FONT_LABEL, fill=(0, 0, 0))

    line1 = f"{label_text1}. {label_text2}. {label_text3}. Подпись: ______________"
    line1_w = FONT_LABEL.getbbox(line1)[2]
    block_x = (A4_WIDTH_PX - line1_w) // 2
    draw.text((block_x, 50), line1, font=FONT_LABEL, fill=(0, 0, 0))

    # === Изображения на странице ===
    start, end = page_num * IMAGES_PER_PAGE, (page_num + 1) * IMAGES_PER_PAGE
    for idx, (img, fname) in enumerate(zip(all_images[start:end], all_files[start:end])):
        row, col = divmod(idx, COLS)

        img_ratio = img.width / img.height
        cell_ratio = CELL_WIDTH / CELL_HEIGHT

        if img_ratio > cell_ratio:
            new_width = CELL_WIDTH
            new_height = int(CELL_WIDTH / img_ratio)
        else:
            new_height = CELL_HEIGHT - 60
            new_width = int(new_height * img_ratio)

        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        x = col * CELL_WIDTH + (CELL_WIDTH - new_width) // 2
        y = HEADER_HEIGHT + row * CELL_HEIGHT + 10

        result.paste(img_resized, (x, y))

        caption = os.path.splitext(fname)[0]
        caption_w = caption_font.getbbox(caption)[2]
        caption_x = col * CELL_WIDTH + (CELL_WIDTH - caption_w) // 2
        caption_y = y + new_height + 5
        draw.text((caption_x, caption_y), caption, font=caption_font, fill=(0, 0, 0))
    
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    output_filename = f"{label_text1}. {label_text2}. {label_text3}. Страница {page_num + 1}.png"
    result.save(os.path.join(RESULT_FOLDER, output_filename), dpi=(DPI, DPI))
    print(f"✅ Сохранено: {output_filename}")