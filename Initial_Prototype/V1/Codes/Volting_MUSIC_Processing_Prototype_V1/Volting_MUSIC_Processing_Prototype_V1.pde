import processing.serial.*;
import javax.sound.midi.*;

Serial myPort;
Synthesizer synth;
MidiChannel channel;

// ===== ANGLES =====
float roll = 0;
float pitch = 0;

// ===== VOLUME =====
int volume = 0;

// ===== MIDI =====
int lastNote = -1;
int lastOctave = -1;

// ===== UI =====
boolean instrumentSelected = false;
String[] instruments = {"Piano", "Guitar", "Trumpet", "Flute", "Cello", "Crystal", "Oboe", "Violin"};
int[] instrumentValues = {0, 24, 56, 73, 42, 98, 68, 40};
int selectedInstrument = 0;

void setup() {
  size(600, 400);

  println("Available serial ports:");
  for (String s : Serial.list()) {
    println(s);
  }

  try {
    synth = MidiSystem.getSynthesizer();
    synth.open();
    channel = synth.getChannels()[0];
    println("MIDI synthesizer ready.");
  } catch (Exception e) {
    println("Error opening MIDI synthesizer: " + e.getMessage());
    exit();
  }
}

void draw() {
  background(0);
  fill(255);
  textSize(16);
  textAlign(CENTER, TOP);

  if (!instrumentSelected) {
    text("Choose an instrument:", width / 2, 20);

    for (int i = 0; i < instruments.length; i++) {
      stroke(255);
      fill(0);
      rect(width / 2 - 100, 60 + i * 40, 200, 30);

      fill(255);
      textAlign(CENTER, CENTER);
      text(instruments[i], width / 2, 60 + i * 40 + 15);
    }

  } else {
    text("Selected instrument: " + instruments[selectedInstrument], width / 2, 20);

    text("Roll: " + nf(roll, 1, 2), width / 2, 60);
    text("Pitch: " + nf(pitch, 1, 2), width / 2, 90);

    text("Volume (Distance): " + volume + " cm", width / 2, 120);
    text("Current MIDI note: " + (lastNote == -1 ? "-" : lastNote), width / 2, 160);
    text("Current MIDI octave: " + (lastOctave == -1 ? "-" : lastOctave), width / 2, 190);
  }
}

void mousePressed() {
  if (!instrumentSelected) {
    for (int i = 0; i < instruments.length; i++) {
      if (mouseX >= width / 2 - 100 && mouseX <= width / 2 + 100 &&
          mouseY >= 60 + i * 40 && mouseY <= 90 + i * 40) {

        selectedInstrument = i;
        instrumentSelected = true;
        channel.programChange(instrumentValues[selectedInstrument]);

        myPort = new Serial(this, "COM4", 115200);
        myPort.bufferUntil('\n');

        println("Selected instrument: " + instruments[selectedInstrument]);
      }
    }
  }
}

void serialEvent(Serial p) {
  if (!instrumentSelected) return;

  String line = p.readStringUntil('\n');
  if (line == null) return;

  line = line.trim();

  // ===== ROLL → NOTE =====
  if (line.startsWith("ROLL:")) {
    try {
      roll = Float.parseFloat(line.substring(5).trim());

      // 🔧 correction angle négatif
      if (roll < 0) roll += 360;

      int note = mapAngleToNote(roll);

      if (note != lastNote && lastOctave != -1) {
        stopLastNote();
        lastNote = note;
        playMidiNote(lastNote, lastOctave, volume);
      }

    } catch (Exception e) {
      println("Error parsing ROLL: " + e.getMessage());
    }
  }

  // ===== PITCH → OCTAVE =====
  else if (line.startsWith("PITCH:")) {
    try {
      pitch = Float.parseFloat(line.substring(6).trim());

      // 🔧 correction angle négatif
      if (pitch < 0) pitch += 360;

      int octave = mapAngleToOctave(pitch);

      if (octave != lastOctave) {
        stopLastNote();
        lastOctave = octave;

        if (lastNote != -1) {
          playMidiNote(lastNote, lastOctave, volume);
        }
      }

    } catch (Exception e) {
      println("Error parsing PITCH: " + e.getMessage());
    }
  }

  // ===== VOLUME =====
  else if (line.startsWith("Volume:")) {
    try {
      int newVolume = int(line.substring(7).trim());

      if (newVolume != volume) {
        volume = newVolume;

        if (lastNote != -1 && lastOctave != -1) {
          adjustVolume(volume);
        }
      }

    } catch (Exception e) {
      println("Error parsing Volume: " + e.getMessage());
    }
  }
}

// ===== MAPPING =====

int mapAngleToNote(float angle) {
  int n = (int)map(angle, 0, 360, 1, 12);
  return constrain(n, 1, 12);
}

int mapAngleToOctave(float angle) {
  int o = (int)map(angle, 0, 360, 2, 6);
  return constrain(o, 2, 6);
}

// ===== MIDI =====

int noteToMidiNumber(int note, int octave) {
  return (octave + 1) * 12 + (note - 1);
}

void playMidiNote(int note, int octave, int distance) {
  if (channel == null) return;

  int midiNote = noteToMidiNumber(note, octave);

  int velocity = (distance >= 400) ? 127 :
                 (distance <= 20 ? 0 :
                 (int)map(distance, 20, 400, 0, 127));

  velocity = constrain(velocity, 0, 127);

  if (velocity > 0) {
    channel.noteOn(midiNote, velocity);
  }
}

void adjustVolume(int distance) {
  if (channel == null) return;

  int velocity = (distance >= 400) ? 127 :
                 (distance <= 20 ? 0 :
                 (int)map(distance, 20, 400, 0, 127));

  velocity = constrain(velocity, 0, 127);

  int midiNote = noteToMidiNumber(lastNote, lastOctave);

  if (velocity == 0) {
    stopLastNote();
    lastNote = -1;
    lastOctave = -1;
  } else {
    channel.controlChange(7, velocity);
  }
}

void stopLastNote() {
  if (lastNote != -1 && lastOctave != -1 && channel != null) {
    channel.noteOff(noteToMidiNumber(lastNote, lastOctave));
  }
}

void stop() {
  stopLastNote();
  if (synth != null && synth.isOpen()) synth.close();
  if (myPort != null) myPort.stop();
  super.stop();
}
