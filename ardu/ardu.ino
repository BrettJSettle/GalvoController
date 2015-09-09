char lasers[4];
int laser;
float val;
void setup() {
  // put your setup code here, to run once:
  pinMode(7, OUTPUT);
  pinMode(11, OUTPUT);
  pinMode(9, INPUT);
  pinMode(13, INPUT);
  Serial.begin(9600);
}

int getPinNum(char c){
  if (int(c) > int('9'))
    return int(c) - 87;
   else
    return int(c) - 48;
}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available()){
    char type = Serial.read();
    if (type == 'D'){
      Serial.readBytes(lasers, 4);
      laser = getPinNum(lasers[0]);
      digitalWrite(7, lasers[1] == 48 ? LOW : HIGH);
      Serial.print(7);
      Serial.print(" is ");
      Serial.println(digitalRead(9));
      laser = getPinNum(lasers[2]);
      digitalWrite(11, lasers[3] == 48 ? LOW : HIGH);
      Serial.print(11);
      Serial.print(" is ");
      Serial.println(digitalRead(13));
    } else if (type == 'A') {
      val = Serial.readStringUntil(' ').toFloat();
      analogWrite(3, int(val*10));
      Serial.print(analogRead(5));
      Serial.print(", ");
      val = Serial.readStringUntil(';').toFloat();
      analogWrite(5, int(val*10));
      Serial.println(analogRead(3));
    }
  }
}
