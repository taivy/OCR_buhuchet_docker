from PIL import Image, ImageChops

def crop_frames(im, i=0):
    bg = Image.new(im.mode, im.size, im.getpixel((255,255)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 1.0, -10)
    bbox = diff.getbbox()
    if bbox:
        #im.save("%s.jpg" % str(i), "JPEG") 
        return im.crop(bbox)
