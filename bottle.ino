#include <Wire.h>                // include the PRIZM library in the sketch
#include <PRIZM.h>               // include the PRIZM library in the sketch
PRIZM prizm;                     // instantiate a PRIZM object “prizm” so we can use its functions

String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete
String outputString = "";        // a string to hold outgoing data

int cmd = 0;                     // an integer to store the cmd
String cmdStr = "";              // a string to store the cmd

// ======== ARM DEFINES (ADDED) ========
#define ARM_L_PIN 3   // digital pin 3 for left arm
#define ARM_R_PIN 2   // digital pin 2 for right arm
#define ARM_L_MIN 90  // min degree for left arm
#define ARM_L_MAX 130 // max  for left arm
#define ARM_R_MIN 40  // min degree for right arm
#define ARM_R_MAX 90  // max degree for right arm

//Motors (not changing your existing setMotorPowers, just defining)
#define LEFT_MOTOR 1
#define RIGHT_MOTOR 2

// --------------ARM CONTROL---------
// (ADDED FUNCTIONS)
void arm_grab(){
  prizm.setServoPosition(ARM_L_PIN, ARM_L_MAX);  // rotate servo3 to 130 degrees
  prizm.setServoPosition(ARM_R_PIN, ARM_R_MIN);  // rotate servo2 to 40 degrees
}

void arm_release(){
  prizm.setServoPosition(ARM_L_PIN, ARM_L_MIN);  // rotate servo3 to 90 degrees
  prizm.setServoPosition(ARM_R_PIN, ARM_R_MAX);  // rotate servo2 to 90 degrees
}

void setup() {
  prizm.PrizmBegin();            // start prizm
  prizm.setMotorInvert(1,1);     // invert the direction of DC Motor 1 to harmonize the direction of opposite facing drive motors
                                 
  Serial.begin(9600);            // initialize serial:
  
  // reserve 20/10 bytes for the string:
  inputString.reserve(20);
  outputString.reserve(20);
  cmdStr.reserve(10);

  // optionally start with open arm (not required)
  // arm_release();
}

void loop() {
  if (stringComplete) {
    cmdStr = inputString.substring(0,1);   // here we only read the first char, and ignore the remainings. In the future, you can design your own msg format to transfer more information
    cmd = cmdStr.toInt();                  // convert string cmd to integer cmd
    
    switch (cmd) {
      // echo
      case 1:{
        outputString += "1";               // everytime we put the original cmd to our outputString, to tell Pi know we get the cmd
        break;
      }
      // turn left
      case 2:{
        outputString += "2";               
        prizm.setMotorPowers(-10,10);      
        break;
      }
      // turn right
      case 3:{
        outputString += "3";               
        prizm.setMotorPowers(10,-10);      
        break;
      }
      // read sonic sensor connected to D3 on the controller
      case 4:{
        outputString = "";             
        outputString += prizm.readSonicSensorCM(3); 
        break;
      }
      // break the motor
      case 5:{
        outputString += "5";               
        prizm.setMotorPowers(125,125);
        break;
      }
      case 6:{
        outputString += "6";               
        prizm.setMotorPowers(10,10);
        break;
      }
      case 7:{
        outputString += "7";               
        prizm.setMotorPowers(-10,-10);
        // delay(2850);
        break;
      }
      // ======== NEW COMMANDS FOR ARM ========
      case 8:{                  // grab
        outputString += "8";
        arm_grab();
        break;
      }
      case 9:{                  // release
        outputString += "9";
        arm_release();
        break;
      }
    }
    
    Serial.println(outputString);          // println helps us to send back msg with a '\n' at the end
    
    // clear the variables to wait for another cmd sending
    inputString = "";
    outputString = "";
    cmdStr = "";
    cmd = 0;
    stringComplete = false;                 //
  }
}


void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read(); 
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag
    // so the main loop can do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    } 
  }
}
