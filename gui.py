#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Gui
"""

from PyQt5.QtWidgets import (QWidget,
                             QPushButton,
                             QApplication,
                             QSplitter,
                             QMainWindow,
                             QFileDialog,
                             QGridLayout,
                             QFrame)
from PyQt5.QtCore import Qt, QTimer, QRect
import clip
from ui import Ui_MainWindow
from cell_ui import Ui_Cell
import struct


class Cell(QWidget, Ui_Cell):

    def __init__(self, parent, clip, x, y):
        super(Cell, self).__init__(parent)

        self.pos_x, self.pos_y = x, y

        self.clip = clip
        self.blink, self.color = False, None
        self.setupUi(self)

        if clip:
            self.clip_name.setText(clip.name)
            self.start_stop.clicked.connect(parent.onStartStopClick)
            self.edit.clicked.connect(parent.onEdit)
        else:
            self.start_stop.setEnabled(False)
            self.clip_position.setEnabled(False)
            self.edit.setText("Add Clip...")
            self.edit.clicked.connect(parent.onAddClipClick)


class Gui(QMainWindow, Ui_MainWindow):

    GREEN = "#frame { background-color: rgb(0,230,0);}"
    BLUE = "#frame { background-color: rgb(0, 130, 240);}"
    RED = "#frame { background-color: rgb(240, 0, 0);}"
    PURPLE = "#frame { background-color: rgb(130, 0, 240);}"
    WHITE = "#frame { background-color: rgb(255, 255, 255);}"

    STATE_COLORS = {clip.Clip.STOP: RED,
                    clip.Clip.STARTING: GREEN,
                    clip.Clip.START: GREEN,
                    clip.Clip.STOPPING: RED}
    STATE_BLINK = {clip.Clip.STOP: False,
                   clip.Clip.STARTING: True,
                   clip.Clip.START: False,
                   clip.Clip.STOPPING: True}

    BLINK_DURATION = 200
    PROGRESS_PERIOD = 100

    def __init__(self, song):
        super(Gui, self).__init__()
        self.setupUi(self)
        self.setWindowTitle('Super Boucle')
        self.gridLayout.setContentsMargins(5, 5, 5, 5)
        self.show()

        self.actionOpen.triggered.connect(self.onActionOpen)
        self.actionSave.triggered.connect(self.onActionSave)
        self.actionSave_As.triggered.connect(self.onActionSaveAs)
        self.master_volume.valueChanged.connect(self.onMasterVolumeChange)
        self.clip_name.textChanged.connect(self.onClipNameChange)
        self.clip_volume.valueChanged.connect(self.onClipVolumeChange)
        self.beat_diviser.valueChanged.connect(self.onBeatDiviserChange)
        self.frame_offset.valueChanged.connect(self.onFrameOffsetChange)
        self.beat_offset.valueChanged.connect(self.onBeatOffsetChange)

        self.blktimer = QTimer()
        self.blktimer.state = False
        self.blktimer.timeout.connect(self.toogleBlinkButton)

        self.disptimer = QTimer()
        self.disptimer.start(self.PROGRESS_PERIOD)
        self.disptimer.timeout.connect(self.updateProgress)

        # Avoid missing song attribute on master volume changed
        self.song = song
        self.initUI(song)

    def initUI(self, song):

        self.groupBox.setEnabled(False)

        self.master_volume.setValue(song.volume*256)

        self.btn_matrix = [[None for x in range(song.height)]
                           for x in range(song.width)]
        self.state_matrix = [[-1 for x in range(song.height)]
                             for x in range(song.width)]

        for i in reversed(range(self.gridLayout.count())):
            self.gridLayout.itemAt(i).widget().close()
            self.gridLayout.itemAt(i).widget().setParent(None)

        for x in range(song.width):
            for y in range(song.height):
                clip = song.clips_matrix[x][y]
                cell = Cell(self, clip, x, y)
                self.btn_matrix[x][y] = cell
                self.gridLayout.addWidget(cell, x, y)

        song.registerUI(self.update)
        self.song = song
        self.update()

    def onStartStopClick(self):
        clip = self.sender().parent().parent().clip
        self.song.toogle(clip.x, clip.y)

    def onEdit(self):
        self.last_clip = self.sender().parent().parent().clip
        if self.last_clip:
            self.groupBox.setEnabled(True)
            self.groupBox.setTitle(self.last_clip.name)
            self.clip_name.setText(self.last_clip.name)
            self.frame_offset.setValue(self.last_clip.frame_offset)
            self.beat_offset.setValue(self.last_clip.beat_offset)
            self.beat_diviser.setValue(self.last_clip.beat_diviser)
            self.clip_volume.setValue(self.last_clip.volume*256)
            self.clip_description.setText("Good clip !")

    def onAddClipClick(self):
        sender = self.sender().parent().parent()
        audio_file, a = QFileDialog.getOpenFileName(self,
                                                    'Open Clip file',
                                                    ('/home/joe/git'
                                                     '/superboucle/'),
                                                    'All files (*.*)')
        if audio_file:
            new_clip = clip.Clip(audio_file)
            sender.clip = new_clip
            sender.clip_name.setText(new_clip.name)
            sender.start_stop.clicked.connect(self.onStartStopClick)
            print(sender.edit.text())
            sender.edit.setText("Edit")
            sender.edit.clicked.disconnect(self.onAddClipClick)
            sender.edit.clicked.connect(self.onEdit)
            sender.start_stop.setEnabled(True)
            sender.clip_position.setEnabled(True)
            self.song.add_clip(new_clip, sender.pos_x, sender.pos_y)
            self.update()

    def onMasterVolumeChange(self):
        self.song.volume = (self.master_volume.value() / 256)

    def onClipNameChange(self):
        self.last_clip.name = self.clip_name.text()
        self.groupBox.setTitle(self.last_clip.name)
        tframe = self.btn_matrix[self.last_clip.x][self.last_clip.y]
        tframe.clip_name.setText(self.last_clip.name)

    def onClipVolumeChange(self):
        self.last_clip.volume = (self.clip_volume.value() / 256)

    def onBeatDiviserChange(self):
        self.last_clip.beat_diviser = self.beat_diviser.value()

    def onFrameOffsetChange(self):
        self.last_clip.frame_offset = self.frame_offset.value()

    def onBeatOffsetChange(self):
        self.last_clip.beat_offset = self.beat_offset.value()

    def onActionSave(self):
        if self.song.file_name:
            self.song.save()
            print("File saved")
        else:
            self.onActionSaveAs()

    def onActionSaveAs(self):
        self.song.file_name, a = (
            QFileDialog.getSaveFileName(self,
                                        'Save As',
                                        '/home/joe/git/superboucle/',
                                        'Super Boucle Song (*.sbl)'))
        if self.song.file_name:
            self.song.save()
            print("File saved to : {}".format(self.song.file_name))

    def onActionOpen(self):
        file_name, a = (
            QFileDialog.getOpenFileName(self,
                                        'Open file',
                                        '/home/joe/git/superboucle/',
                                        'Super Boucle Song (*.sbl)'))
        if file_name:
            self.setEnabled(False)
            self.initUI(clip.load_song_from_file(file_name))
            self.setEnabled(True)

    def update(self):
        for clp in self.song.clips:
            # print("updating clip at {0} {1}".format(clp.x, clp.y))
            if clp.state != self.state_matrix[clp.x][clp.y]:
                self.setCellColor(clp.x,
                                  clp.y,
                                  self.STATE_COLORS[clp.state],
                                  self.STATE_BLINK[clp.state])
                self.state_matrix[clp.x][clp.y] = clp.state

    def setCellColor(self, x, y, color, blink=False):
        self.btn_matrix[x][y].setStyleSheet(color)
        self.btn_matrix[x][y].blink = blink
        self.btn_matrix[x][y].color = color
        if blink and not self.blktimer.isActive():
            self.blktimer.state = False
            self.blktimer.start(self.BLINK_DURATION)
        if not blink and self.blktimer.isActive():
            if not any([btn.blink for line in self.btn_matrix
                        for btn in line]):
                self.blktimer.stop()

    def toogleBlinkButton(self):
        for line in self.btn_matrix:
            for btn in line:
                if btn.blink:
                    if self.blktimer.state:
                        btn.setStyleSheet(btn.color)
                    else:
                        btn.setStyleSheet("")

        self.blktimer.state = not self.blktimer.state

    def updateProgress(self):
        for line in self.btn_matrix:
            for btn in line:
                if btn.clip:
                    btn.clip_position.setValue((
                        (btn.clip.last_offset / btn.clip.length) * 100))


class PadUI():

    NOTEON = 0x9
    NOTEOFF = 0x8

    pad_note_to_coord = {36: (0, 0), 38: (0, 1), 40: (0, 2), 41: (0, 3),
                         48: (1, 0), 50: (1, 1), 52: (1, 2), 53: (1, 3),
                         60: (2, 0), 62: (2, 1), 64: (2, 2), 65: (2, 3),
                         72: (3, 0), 74: (3, 1), 76: (3, 2), 77: (3, 3)}

    pad_coord_to_note = [[36, 38, 40, 41],
                         [48, 50, 52, 53],
                         [60, 62, 64, 65],
                         [72, 74, 76, 77]]

    pad_state_to_color = {clip.Clip.STOP: 12,
                          clip.Clip.STARTING: 13,
                          clip.Clip.START: 14,
                          clip.Clip.STOPPING: 15}

    def __init__(self, width, height):
        self.state_matrix = [[-1 for x in range(height)]
                             for x in range(width)]

    def updatePad(self, song):
        res = []
        song.updatePadUI = False
        for x in range(song.width):
            for y in range(song.height):
                clip = song.clips_matrix[x][y]
                if clip:
                    if clip.state != self.state_matrix[x][y]:
                        print("Will update pad cell {0} {1} to state {2}".
                              format(x, y, clip.state))
                        res.append(self.generateNote(x, y, clip.state))
                        self.state_matrix[x][y] = clip.state
        return res

    def processNote(self, song, notes):
        for note in notes:
            if len(note) == 3:
                status, pitch, vel = struct.unpack('3B', note)
                print("Note received {0} {1} {2}".
                      format(status, pitch, vel))
                try:
                    x, y = self.getXY(pitch)

                    if status >> 4 == self.NOTEOFF and x >= 0 and y >= 0:
                        song.toogle(x, y)
                except KeyError:
                    pass

    def getXY(self, note):
        return self.pad_note_to_coord[note]

    def generateNote(self, x, y, state):
        print("Generate note for cell {0} {1} and state {2}".
              format(x, y, state))
        note = self.pad_coord_to_note[x][y]
        velocity = self.pad_state_to_color[state]
        return (self.NOTEON, note, velocity)



def main():
    app = QApplication()
    clip = Clip('beep-stereo.wav', beat_diviser=4, frame_offset=0, beat_offset=1)  # 1500
    song = Song(8, 8)
    song.add_clip(clip, 1, 2)

    app = QApplication()
    Gui(song)
    app.exec_()
   


if __name__ == '__main__':
    main()
