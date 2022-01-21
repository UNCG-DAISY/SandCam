# Written by Jacob Stasiewicz and Evan Goldstein
#
# MIT License


#import packages
from gpiozero import Button, LED
from picamera import PiCamera
import os
import glob
import datetime
from gps import *
import subprocess
from PIL import Image
import numpy as np
from pycoral.utils import edgetpu
from pycoral.utils import dataset
from pycoral.adapters import common
from pycoral.adapters import classify

#define gpio pins and variables
pwd = os.getcwd()
camera = PiCamera()
camera.resolution = (2048,2048)
led = LED(13)
previewbtn = Button(4, hold_time=2) 
counter = 1

#GPS stuff
gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 

#TFLITE stuff
path_to_model = "./models/SandCam_QAT_notdense_edgetpu.tflite"
# Initialize the TF interpreter
interpreter = edgetpu.make_interpreter(path_to_model)
interpreter.allocate_tensors()
#uncomment lines below to debug and look at expected I/O
#print(interpreter.get_input_details())
#print(interpreter.get_output_details())

#make new directory and create text file within

#direcname = str(input("name your file: "))
direcname = str(datetime.datetime.now())
newpath = pwd + '/' + direcname
croppath = pwd + '/' + direcname + '/crop'
os.makedirs(newpath)
os.makedirs(croppath)

print("Made a Directory for this session:")
print(newpath)

txtfile = open(newpath + '/' + direcname + '.csv', 'w+')
txtfile.write('img, date/time (UTC), lat, lon, alt(m), 0.05, 0.10, 0.16, 0.15, 0.30, 0.50, 0.75, 0.84, 0.90, 0.95, d50, std dev, skewness, kurtosis '"\n")
txtfile.close()
textarg = str(newpath + '/' + direcname + '.csv')
croparg = str(croppath)

print("Made a txt file for this session")

#define functions
def capture():
	global counter
	#get GNSS data
	report = gpsd.next()
	lat1 = "-9999"
	lon1 = "-9999"
	alt1 = "-9999"
	if report['class'] == 'TPV':
		if getattr(report,'lat',0.0)!=0:
			lat1 = str(getattr(report,'lat',0.0))
		if getattr(report,'lon',0.0)!=0:
			lon1 = str(getattr(report,'lon',0.0))
		if getattr(report,'alt','nan')!= 'nan':
			alt1 = str(getattr(report,'alt','nan'))


	camera.capture(newpath + '/' + str(counter) + '.jpg')
	im = Image.open(str(newpath + '/' + str(counter) + '.jpg'))
	crop_img = crop_center(im,1024,1024)
	crop_img.save(croppath + '/crop' + str(counter) + '.jpg')
	txtfile = open(newpath + '/' + direcname + '.csv', 'a')
	txtfile.write( str(counter) + ',' + str(datetime.datetime.now()) +
	',' + lat1 + ',' + lon1 + ','+ alt1 + ',')
	txtfile.close()
	print(lat1)
	print(lon1)
	print(alt1)
	#prediction step
	#with pyDGS
	pyDGS()
	#with TFLite:
	TFlitePred(crop_img)
	print('that was picture:')
	print(counter)
	counter = counter + 1
	

def previewon():
	camera.start_preview()
	subprocess.call(["./ringledon.sh"])
	
def previewoff():
	camera.stop_preview()
	subprocess.call(["./ringledoff.sh"])

def crop_center(pil_img, crop_width, crop_height):
   img_width, img_height = pil_img.size
   return pil_img.crop(((img_width - crop_width) // 2,
                          (img_height - crop_height) // 2,
                          (img_width + crop_width) // 2,
                          (img_height + crop_height) // 2))
                          
def pyDGS():
	global textarg 
	list_of_files_crop = glob.glob(croppath + '/*.jpg')
	latest_file_crop = str(max(list_of_files_crop, key=os.path.getctime))
	print("using pyDGS to get grain size")
	subprocess.call(["python3", "example_test.py", latest_file_crop, textarg])
	print("ready for next picture")

def TFlitePred(crop_img):
    #get image in the correct shape,size, format
    converted_crop = np.array(crop_img, dtype=np.float32)
    r_crop_img = converted_crop/255
    crop_img_exp = np.expand_dims(r_crop_img, axis=0)
 
    common.set_input(interpreter, crop_img_exp)
    interpreter.invoke()
    
    predictions = common.output_tensor(interpreter, 0)
    
    print(predictions)
    return predictions

	
print("ready for a picture. Press trigger to preview, hold for 2 seconds for a picture.")

#While function to just run

while True:
				
	#Everything else
	led.source = previewbtn
	previewbtn.when_pressed = previewon
	previewbtn.when_held = capture
	previewbtn.when_released = previewoff 
		
#except(KeyboardInterrupt, SystemExit):
#	print ("Done.\nExiting")