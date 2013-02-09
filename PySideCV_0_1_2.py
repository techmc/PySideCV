import sys
import cv2
import cv2.cv as cv
from PySide import QtGui
from PySide import QtCore
from PySide.QtGui import QColor
from PySide.QtGui import QImage
from PySide.QtCore import Qt
from PySide.QtCore import QPoint

camcapture = cv.CaptureFromCAM(0)

class OpenCVQImage(QtGui.QImage):
    def __init__(self, opencvBgrImg):
        
        depth, nChannels = opencvBgrImg.depth, opencvBgrImg.nChannels
        if depth != cv.IPL_DEPTH_8U or nChannels != 3:
            raise ValueError("the input image must be 8-bit, 3-channel")
        w, h = cv.GetSize(opencvBgrImg)
        opencvRgbImg = cv.CreateImage((w, h), depth, nChannels)
        # it's assumed the image is in BGR format
        cv.CvtColor(opencvBgrImg, opencvRgbImg, cv.CV_BGR2RGB)
        self._imgData = opencvRgbImg.tostring()
        super(OpenCVQImage, self).__init__(self._imgData, w, h, \
            QtGui.QImage.Format_RGB888)

class drawCanny(QtGui.QImage):
    def __init__(self, frame, threshMin, threshMax):
        
        im_gray = cv.CreateImage(cv.GetSize(frame), frame.depth, 1) # only 1 channel, can't convert to qimage
        cv.CvtColor(frame, im_gray, cv.CV_RGB2GRAY)
        im_cann = cv.CreateImage(cv.GetSize(im_gray), im_gray.depth, im_gray.channels)
        #cv.Canny(im_gray, im_cann, 10, 100, 3)
        cv.Canny(im_gray, im_cann, threshMin, threshMax, 3)
        
        cv.CvtColor(im_cann, frame, cv.CV_GRAY2RGB)

class PySideCam(QtGui.QWidget):
    
    def __init__(self):
        super(PySideCam, self).__init__()
        
        self.initUI()
        
    def initUI(self):

        dimx = 800
        dimy = 520

        self.threshMin = 10
        self.threshMax = 100 #needed?

        self.setGeometry(300, 300, dimx, dimy)
        self.setWindowTitle('PySideCV')
        self.setWindowIcon(QtGui.QIcon('web.png'))

        self.checkbox = QtGui.QCheckBox("Show Canny", self)
        self.checkbox.toggle()
        self.checkbox.setCheckState( Qt.Unchecked )

        self.sliderMin = QtGui.QSlider(Qt.Horizontal, self)
        self.sliderMin.setRange(0, 75)
        self.sliderMin.setValue(10)
        self.sliderMin.sliderReleased.connect(self.sliderChanged)

        self.sliderMax = QtGui.QSlider(Qt.Horizontal, self)
        self.sliderMax.setRange(76, 300)
        self.sliderMax.setValue(100) # or just sliderMin * 3
        self.sliderMax.sliderReleased.connect(self.sliderChanged)


        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.checkbox)
        vbox.addWidget(self.sliderMin)
        vbox.addWidget(self.sliderMax)
                
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addLayout(vbox)
        
        self.setLayout(hbox)

        self.show()
        
    def sliderChanged(self):

        self.threshMin = self.sliderMin.value()
        self.threshMax = self.sliderMax.value()
        
        
    def setValue(self, value):

        self.slider.setValue(value)

    def paintEvent(self, event=None):
        
        qp = QtGui.QPainter()

        qp.begin(self)
        self.drawFrames(qp)
        qp.end()

        self.update()
        
    def drawFrames(self, qp):
        
        q_frame = cv.QueryFrame(camcapture) # capture frame

        if QtGui.QAbstractButton.isChecked(self.checkbox): # perform Canny is selected
            drawCanny(q_frame, self.threshMin, self.threshMax)

        frame = q_frame
        image = OpenCVQImage(frame) # convert to QImage
        qp.drawImage(QPoint(20, 20), image)

def main():
    
    app = QtGui.QApplication(sys.argv)
    ex = PySideCam()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
