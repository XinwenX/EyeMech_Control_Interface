#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// Pulse Range of X/Y: Need to be adjusted based on hardware calibration
// X range(degree): 40-140 (mid: 90), Y range(degree): 50-100 (mid: 75)
// PWM range(2.85/degree): 150 ~0 degree， 665 ~180 degree, 410 ~90 degree
#define X_DEGREE_MIN 40
#define X_DEGREE_MAX 140
#define Y_DEGREE_MIN 50
#define Y_DEGREE_MAX 100

#define SERVOMIN  150 // this is the 'minimum' pulse length count (out of 4096)
#define PULSE_Ratio 2.85

// Pulse Range of lid
#define SERVOMIN_LID 330   
#define SERVOMAX_LID 480   

int Fullrange = SERVOMIN_LID+SERVOMAX_LID-10;

// port cache
String inputString = "";
bool stringComplete = false;

// Current pulse of lid(left-top,left-bottom,right-top,right-bottom), initial value is fully open
int uplidpulse = SERVOMIN_LID;
int lolidpulse = SERVOMAX_LID;
int altuplidpulse = SERVOMAX_LID;
int altlolidpulse = SERVOMIN_LID;
// Pulse step for lid when receiving command from mouse wheel
const int LID_STEP_PULSE = 5;

void update_lid() {
  pwm.setPWM(2, 0, uplidpulse);
  pwm.setPWM(3, 0, lolidpulse);
  pwm.setPWM(4, 0, altuplidpulse);
  pwm.setPWM(5, 0, altlolidpulse);
}

void blink() {
  // close lid
  pwm.setPWM(2, 0, SERVOMAX_LID);
  pwm.setPWM(3, 0, SERVOMIN_LID);
  pwm.setPWM(4, 0, SERVOMIN_LID);
  pwm.setPWM(5, 0, SERVOMAX_LID);
  
  delay(250);

  // open lid
  update_lid();
}

void update_lid_pulse(int delta) {
  int d_pulse = delta * LID_STEP_PULSE;
  uplidpulse -= d_pulse;
  uplidpulse = constrain(uplidpulse, SERVOMIN_LID, SERVOMAX_LID);
  altuplidpulse = Fullrange - uplidpulse;

  lolidpulse += d_pulse;
  lolidpulse = constrain(lolidpulse, SERVOMIN_LID, SERVOMAX_LID);
  altlolidpulse = Fullrange - lolidpulse;

  update_lid();
}

void update_eye(float x, float y) {
  int xPulse = SERVOMIN + PULSE_Ratio * map(x, -50, 50, X_DEGREE_MIN, X_DEGREE_MAX);
  int yPulse = SERVOMIN + PULSE_Ratio * map(y, -50, 50, Y_DEGREE_MIN, Y_DEGREE_MAX);
  pwm.setPWM(0, 0, xPulse);
  pwm.setPWM(1, 0, yPulse);
}

void setup() {
  Serial.begin(9600);
  //Serial.println("Arduino: Ready to receive X,Y / δ / BLINK commands");
  
  pwm.begin();
  pwm.setPWMFreq(60); // Analog servos run at ~60 Hz updates

  // Initialize lid
  update_lid();

  // Initialize eye
  update_eye(0, 0);

  delay(10);
}

void loop() {
  // Read serial data, if available
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }

  if (stringComplete) {
    inputString.trim();
    //Serial.print("Data Received: "); Serial.println(inputString);

    if (inputString == "BLINK") {
      blink();
    }
    else if (inputString.startsWith("LID")) {
      // δ: the amount of lid update
      int idx_1 = inputString.indexOf(' ');
      int delta = inputString.substring(idx_1 + 1).toInt();
      if (idx_1 != -1) {
        update_lid_pulse(delta); 
      } else{
        Serial.print("Command Error: ");
        Serial.println(inputString);
      }
    }
    else {
      // X,Y commands from "EYE X Y"([-50, 50], [-50, 50] percentage)
      int idx_1 = inputString.indexOf(' ');
      int idx_2 = inputString.indexOf(' ', idx_1 + 1);
      if (idx_1 != -1) {
        float xVal = inputString.substring(idx_1 + 1, idx_2).toFloat();
        float yVal = inputString.substring(idx_2 + 1).toFloat();
        update_eye(xVal, yVal);
      } else{
        Serial.print("Command Error: ");
        Serial.println(inputString);
      }
    }

    // reset the string
    inputString = "";
    stringComplete = false;
  }

  delay(5);
}
