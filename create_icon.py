from PIL import Image, ImageDraw

# Create a new image (256x256 pixels)
img = Image.new('RGB', (256, 256), color='#E8B4B8')
draw = ImageDraw.Draw(img)

# Draw a heart shape (simple)
# Outer circle left
draw.ellipse([30, 80, 130, 180], fill='#C4858C')
# Outer circle right
draw.ellipse([126, 80, 226, 180], fill='#C4858C')
# Triangle bottom
draw.polygon([(30, 180), (226, 180), (128, 240)], fill='#C4858C')

# Save as icon
img.save('icon.ico')
print("✓ icon.ico created successfully!")
print("Location: " + os.path.abspath('icon.ico'))

import os
