import cv2 as cv
import numpy as np
import RPi.GPIO as GPIO
import time

PWMA = 12
PWMB = 13
BIN1 = 20
BIN2 = 16
AIN1 = 26
AIN2 = 6
solenoid_pin = 4
GPIO_TRIGGER = 15 
GPIO_ECHO = 14

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWMA, GPIO.OUT)
GPIO.setup(PWMB, GPIO.OUT)
GPIO.setup(AIN1, GPIO.OUT)
GPIO.setup(AIN2, GPIO.OUT)
GPIO.setup(BIN1, GPIO.OUT)
GPIO.setup(BIN2, GPIO.OUT)
GPIO.setup(solenoid_pin, GPIO.OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

pwmA = GPIO.PWM(PWMA, 1000)
pwmB = GPIO.PWM(PWMB, 1000)
pwmA.start(0)
pwmB.start(0)

def motorA_forward(speed: int):
    GPIO.output(AIN1, GPIO.HIGH)
    GPIO.output(AIN2, GPIO.LOW)
    pwmA.ChangeDutyCycle(speed)
    
def motorA_backward(speed: int):
    GPIO.output(AIN1, GPIO.LOW)
    GPIO.output(AIN2, GPIO.HIGH)
    pwmA.ChangeDutyCycle(speed)

def motorB_forward(speed: int):
    GPIO.output(BIN1, GPIO.HIGH)
    GPIO.output(BIN2, GPIO.LOW)
    pwmB.ChangeDutyCycle(speed)

def motorB_backward(speed: int):
    GPIO.output(BIN1, GPIO.LOW)
    GPIO.output(BIN2, GPIO.HIGH)
    pwmB.ChangeDutyCycle(speed)

def motor_stop():
    GPIO.output(AIN1, GPIO.LOW)
    GPIO.output(AIN2, GPIO.LOW)
    GPIO.output(BIN1, GPIO.LOW)
    GPIO.output(BIN2, GPIO.LOW)
    pwmA.ChangeDutyCycle(0)
    pwmB.ChangeDutyCycle(0)

def activate_solenoid(duration):
    GPIO.output(solenoid_pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(solenoid_pin, GPIO.LOW)

def measure_distance():
    GPIO.output(GPIO_TRIGGER, False)
    time.sleep(0.5)
    
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)
    
    while GPIO.input(GPIO_ECHO) == 0:
        pulse_start = time.time()
    
    while GPIO.input(GPIO_ECHO) == 1:
        pulse_end = time.time()
    
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)


def find_ball(frame):
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    lower_red = np.array([5, 150, 150])
    upper_red = np.array([20, 255, 255])
    mask = cv.inRange(hsv, lower_red, upper_red)
    contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv.contourArea)
        M = cv.moments(largest_contour)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            cv.circle(frame, (cx, cy), 10, (0, 0, 255), -1)
            return cx, cy, cv.contourArea(largest_contour)
    return None, None, 0

def move_robot(cx, cy, area, frame_width):
    if cx is None:
        motorA_forward(60)
        motorB_backward(0)
        print("No object detected, searching...")
        return True
    
    center_x = frame_width // 2
    threshold = 100    

    if abs(cx - center_x) <= threshold:
        print("Object detected")
        distance = measure_distance()
        while distance >= 5:
            print(f"Distance: {distance} cm")
            motorA_forward(60)
            motorB_forward(60)
            distance = measure_distance()
        motor_stop()
        activate_solenoid(1)
        return False
    else:
        if cx < center_x:
            motorA_forward(30)
            motorB_backward(30)
        else:
            motorA_backward(30)
            motorB_forward(30)
        return True

cap = cv.VideoCapture(0)
time.sleep(2)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cx, cy, area = find_ball(frame)
        if not move_robot(cx, cy, area, frame.shape[1]):
            break
        
        cv.imshow('Frame', frame)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass

finally:
    cap.release()
    cv.destroyAllWindows()
    pwmA.stop()
    pwmB.stop()
    GPIO.cleanup()
