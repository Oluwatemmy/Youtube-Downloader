import os

url = input("Enter the YouTube video URL: ")

# Use yt-dlp to download the video
os.system(f'yt-dlp "{url}"')
