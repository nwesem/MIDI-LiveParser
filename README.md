# MIDI-LiveParser
The MIDI-LiveParser is used to parse live input from any MIDI device to
a piano roll matrix in real-time and to play piano roll matrices without
the need of conversion to MIDI format.

The MIDI-LiveParser eases handling of MIDI devices by taking care of
porting (Input and Output) using mido library, clock timings, and parsing
to piano roll matrix using numpy library.

## Usage:
```python
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
```

## Dependencies
See [Requirements](requirements.txt).

##
Copyright 2019 Niclas Wesemann