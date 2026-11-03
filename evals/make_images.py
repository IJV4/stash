from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES = Path(__file__).resolve().parent / "images"
WHITE = "white"
BLACK = "black"
BODY_SIZE = 44
HEADING_SIZE = 64
MARGIN = 60

RECIPE_CARD = (
    (HEADING_SIZE, "Lemon Garlic Roast Chicken"),
    (BODY_SIZE, "Prep and cook: 45 min"),
    (BODY_SIZE, ""),
    (BODY_SIZE, "Ingredients"),
    (BODY_SIZE, "1 whole chicken"),
    (BODY_SIZE, "4 cloves garlic"),
    (BODY_SIZE, "2 lemons"),
    (BODY_SIZE, "3 tbsp olive oil"),
    (BODY_SIZE, "Salt and pepper"),
)
EVENT_POSTER = (
    (HEADING_SIZE, "Harbor Lights Night Market"),
    (BODY_SIZE, ""),
    (HEADING_SIZE, "Saturday 22 May 2027"),
    (BODY_SIZE, "6pm - 11pm"),
    (BODY_SIZE, ""),
    (BODY_SIZE, "Pier 9 Waterfront, Harbor City"),
    (BODY_SIZE, "Street food, music and crafts"),
    (BODY_SIZE, "Free entry"),
)
PRODUCT_SCREENSHOT = (
    (HEADING_SIZE, "AeroPress Go Travel Coffee Press"),
    (BODY_SIZE, "Compact coffee maker for travel"),
    (BODY_SIZE, ""),
    (HEADING_SIZE, "$39.95"),
    (BODY_SIZE, "In stock - free shipping"),
    (BODY_SIZE, ""),
    (HEADING_SIZE, "[ Add to cart ]"),
)
IMAGE_SIZES = {
    "recipe_card.png": ((1100, 760), RECIPE_CARD),
    "event_poster.png": ((1300, 700), EVENT_POSTER),
    "product_screenshot.png": ((1700, 620), PRODUCT_SCREENSHOT),
}


def render(size: tuple[int, int], lines: tuple[tuple[int, str], ...]) -> Image.Image:
    image = Image.new("RGB", size, WHITE)
    draw = ImageDraw.Draw(image)
    y = MARGIN
    for font_size, text in lines:
        draw.text((MARGIN, y), text, fill=BLACK, font=ImageFont.load_default(size=font_size))
        y += round(font_size * 1.4)
    return image


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    for name, (size, lines) in IMAGE_SIZES.items():
        render(size, lines).save(IMAGES / name)


if __name__ == "__main__":
    main()
