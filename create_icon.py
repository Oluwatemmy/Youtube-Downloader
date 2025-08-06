"""
Simple script to create a basic icon for the application
Requires Pillow: pip install pillow
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    def create_icon():
        # Create a 256x256 image with red background
        img = Image.new('RGB', (256, 256), color='#FF0000')
        draw = ImageDraw.Draw(img)
        
        # Draw white circle
        draw.ellipse([40, 40, 216, 216], fill='white')
        
        # Draw play triangle
        triangle = [(100, 90), (180, 128), (100, 166)]
        draw.polygon(triangle, fill='#FF0000')
        
        # Save as different formats
        img.save('icon.png', 'PNG')
        img.save('icon.ico', 'ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        
        # For macOS, create ICNS (requires pillow-heif)
        try:
            img.save('icon.icns', 'ICNS')
        except:
            print("Note: Could not create .icns file. Install pillow-heif for macOS icon support.")
        
        print("Icons created successfully!")
        print("- icon.png (256x256)")
        print("- icon.ico (Windows)")
        if os.path.exists('icon.icns'):
            print("- icon.icns (macOS)")
    
    if __name__ == "__main__":
        create_icon()

except ImportError:
    print("PIL (Pillow) not installed. Run: pip install pillow")
    print("Skipping icon creation - you can add your own icon.ico file.")