#!/usr/bin/env python3
# Copyright 2019 Niclas Wesemann
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
@title           :MIDI-LiveParser.py
@author          :nw
@contact         :niclaswesemann@gmail.com
@created         :04/27/2019
@version         :1.0
@python_version  :3.7.3

The MIDI-LiveParser is used to parse live input from any MIDI device to
a piano roll matrix in real-time and to play piano roll matrices without
the need of conversion to MIDI format.

The MIDI-LiveParser eases handling of MIDI devices by taking care of
porting (Input and Output) using mido library, clock timings, and parsing
to piano roll matrix using numpy library.
"""

import mido
import time
import numpy as np
import matplotlib.pyplot as plt


class LiveParser:
    def __init__(self, port=None, bpm=120, ppq=24, bars=0, end_seq_note=127):
        self.bpm = bpm  # beats per minute
        self.ppq = ppq  # pulses per quarter note
        self.seconds2tick = 60. / (bpm * ppq)  # seconds to tick conversion
        self.current_tick = -1
        self.sequence = []
        self.start_time = time.time()
        self.end_seq_note = end_seq_note
        self.bar_length = ppq * 4
        self.bars = bars
        self.seq_length_ticks = self.bar_length * self.bars
        self.counter_metronome = 0
        self.metronome = 0
        self.in_port = port
        self.current_time = 0.
        self.temp_tick = 0
        self.out_port = None
        self.human = True

    def open_inport(self, callback_function):
        """Opens MIDI input port which this script listens to.

        This method allows you to choose a connected MIDI device and a
        callback function that depends on your task.

        Args:
            callback_function: The callback function depending on your task,
            e.g. print MIDI messages on terminal --> print_message
            or create list of MIDI notes --> parse_notes
        """
        avail_ports = mido.get_input_names()
        ports_dict = {i: avail_ports[i] for i in range(len(avail_ports))}
        print("These input ports are available: ", ports_dict)
        if not self.in_port:
            port_num = int(input("Which port would you like to use? "))
            self.in_port = mido.open_input(ports_dict[port_num], callback=callback_function)
        else:
            self.in_port = mido.open_input(self.in_port, callback=callback_function)
        print("Using input port: ", self.in_port)

    def open_outport(self):
        """Opens MIDI output port which this script sends MIDI messages to.

        This method allows to play MIDI messages on a MIDI out port. It will
        try to find fluidsynth to digitally synthesize corresponding MIDI messages.
        If fluidsynth not found it will create virtual MIDI port (LiveParser port)
        that any MIDI device can listen to.
        """
        avail_out_ports = mido.get_output_names()
        ports_dict = {i: avail_out_ports[i] for i in range(len(avail_out_ports))}
        port = None
        for i in range(len(avail_out_ports)):
            if "Synth input" in ports_dict[i]:  # Better way than looking for this string?
                port = ports_dict[i]
        if port:
            self.out_port = mido.open_output(port)
            print("Found FLUID Synth and autoconnected!")
        else:
            self.out_port = mido.open_output("LiveParser port", virtual=True)
            print("Could not find FLUID Synth, created virtual midi port called 'LiveParser port'")

    def update_bpm(self, new_bpm):
        """Updates Beats-per-minute (BPM).

        This method is used in (graphical) user interfaces to update the BPM of
        the LiveParser.

        Args:
            new_bpm: New BPM you want to run the LiveParser now with.
        """
        self.bpm = new_bpm
        self.seconds2tick = 60. / (self.bpm * self.ppq)

    def update_bars(self, bars):
        """Updates the number of bars.

        This method is used in (graphical) user interfaces to update the number
        of bars of the LiveParser.

        Args:
            bars: New number of bars you want the LiveParser to listen to.
        """
        self.bars = bars
        self.seq_length_ticks = self.bar_length * self.bars

    def reset_clock(self):
        """Resets clock of LiveParser.

        This method resets the clock of the LiveParser before it starts listening.
        """
        self.start_time = time.time()
        self.current_tick = -1
        self.metronome = 0
        self.counter_metronome = 0

    def reset_sequence(self):
        """Resets sequence.

        This method resets the list of MIDI notes (the sequence) so that the
        LiveParser can parse a new sequence.
        """
        self.sequence = []

    def clock(self):
        """This is the clock of the LiveParser.

        This method tracks the timing of all played notes. For input and output
        of MIDI notes.
        """
        self.current_time = time.time() - self.start_time
        self.temp_tick = int(self.current_time / self.seconds2tick)
        if self.temp_tick > self.current_tick:
            self.current_tick = self.temp_tick
            # print("clock {}".format(self.current_tick))
            if self.current_tick % self.ppq == 0:
                self.counter_metronome += 1
        if self.current_tick >= self.seq_length_ticks-1:
            if self.sequence:
                return 1
            else:
                print("No note was played - starting over!\n")
                self.reset_clock()
        if self.counter_metronome > self.metronome:
            self.metronome = self.counter_metronome
            print(self.metronome)

    def computer_play(self, prediction):
        """Plays MIDI notes from piano roll matrix.

        This method sends MIDI notes found in the prediction matrix to the
        output port which results in the output port synthesizing the notes.

        Args:
            prediction: A piano roll matrix containing MIDI notes.
        """
        self.human = False
        self.reset_clock()
        play_tick = -1
        old_midi_on = np.zeros(1)
        played_notes = []
        while True:
            done = self.computer_clock()
            if self.current_tick > play_tick:
                play_tick = self.current_tick
                midi_on = np.argwhere(prediction[play_tick] > 0)
                if midi_on.any():
                    for note in midi_on[0]:
                        if note not in old_midi_on:
                            current_vel = int(prediction[self.current_tick,note])
                            # print(current_vel)
                            self.out_port.send(mido.Message('note_on',
                                                note=note, velocity=current_vel))
                            played_notes.append(note)
                else:
                    for note in played_notes:
                        self.out_port.send(mido.Message('note_off', note=note))
                        played_notes.pop(0)

                if old_midi_on.any():
                    for note in old_midi_on[0]:
                        if note not in midi_on:
                            self.out_port.send(mido.Message('note_off', note=note))
                old_midi_on = midi_on

            if done:
                self.human = True
                self.reset_clock()
                break

    def computer_clock(self):
        """This is another clock of the LiveParser.

        This method allows to track the timing when a matrix is played with
        computer_play method.
        """
        self.current_time = time.time() - self.start_time
        self.temp_tick = int(self.current_time / self.seconds2tick)
        if self.temp_tick > self.current_tick:
            self.current_tick = self.temp_tick
            # print("clock {}".format(self.current_tick))
            if self.current_tick % self.ppq == 0:
                self.counter_metronome += 1
        if self.current_tick >= self.seq_length_ticks-1:
            return 1
        if self.counter_metronome > self.metronome:
            self.metronome = self.counter_metronome
            print(self.metronome)

    def print_message(self, msg):
        """Prints MIDI message in MIDI format.

        Args:
            msg: message for callback function.
        """
        print(msg)

    def print_message_bytes(self, msg):
        """Prints MIDI messages in byte format.

        Args:
            msg: message for callback function.
        """
        print(msg.bytes())

    def parse_notes(self, message):
        """Tracks notes that are played when metronome is running.

        This method records all notes that are played when LiveParser
        is online. It is the preliminary step for live parsing to a
        piano roll matrix.

        Args:
            message: message for callback function
        """
        msg = message.bytes()
        # only append midi on and midi off notes
        if 128 <= msg[0] < 160:
            self.sequence.append([self.current_tick, msg[0], msg[1], msg[2]])

        # TODO could be extended to use midi control changes like pitch bend etc.

    def parse_to_matrix(self):
        """Parses sequence of MIDI notes to a matrix of size (length,128).

        This method parses the previously recorded MIDI notes to
        a piano roll (numpy) matrix.

        Returns:
            pianoroll: A piano roll matrix that was recorded when the LiveParser
            was listening.
        """
        # print("Parsing...")
        pianoroll = np.zeros((self.seq_length_ticks, 128))

        for note in self.sequence:
            # print(note)
            # note on range in ints (all midi channels 1-16)
            if 144 <= note[1] < 160:
                pianoroll[note[0]-1, note[2]] = note[3]
            # note off range in ints (all midi channels 1-16)
            elif 128 <= note[1] < 144:
                try:
                    note_on_entry = np.argwhere(pianoroll[:note[0],note[2]])[-1][0]
                    # print(note_on_entry)
                except:
                    note_on_entry = 0
                # some midi instruments send note off message with 0 or constant velocity
                # use the velocity of the corresponding note on message
                # TODO USE VELOCITY OF NOTE ON MESSAGE
                # BUGGY, throws error if you play a note on the last midi tick of the sequence
                if note[3] == 0:
                    last_velocity = pianoroll[note_on_entry, note[2]]
                    pianoroll[note_on_entry+1:note[0]+1, note[2]] = last_velocity
                else:
                    pianoroll[note_on_entry+1:note[0]+1, note[2]] = note[3]

        return pianoroll


if __name__ == '__main__':
    bpm = 120  # beats per minute
    ppq = 24  # pulses per quarter note
    bar_length = ppq * 4  # 4/4
    bars = 2  # how many bars would you like to record?

    midi = LiveParser(bpm=bpm, ppq=ppq, bars=bars, end_seq_note=127)
    midi.open_inport(midi.parse_notes)
    midi.open_outport()
    midi.reset_clock()
    while True:
        status_played_notes = midi.clock()
        if status_played_notes:
            sequence = midi.parse_to_matrix()
            break
    # show results
    plt.imshow(sequence.transpose(1,0), origin='lower')
    plt.show()
