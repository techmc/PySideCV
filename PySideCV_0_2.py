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
    def __init__(self, RGBImg):
        
        #check for correct image format
        depth, nChannels = RGBImg.depth, RGBImg.nChannels
        if depth != cv.IPL_DEPTH_8U or nChannels != 3:
            raise ValueError("the input image must be 8-bit, 3-channel")
        w, h = cv.GetSize(RGBImg)
        #convert RGB image to QImage
        self._imgData = RGBImg.tostring()
        super(OpenCVQImage, self).__init__(self._imgData, w, h, \
            QtGui.QImage.Format_RGB888)


class DrawCanny(QtGui.QImage):
    def __init__(self, frame, thresh_min, thresh_max):
        
        im_gray = cv.CreateImage(cv.GetSize(frame), frame.depth, 1)
        #create grayscale image
        cv.CvtColor(frame, im_gray, cv.CV_RGB2GRAY)
        im_cann = cv.CreateImage(cv.GetSize(im_gray), im_gray.depth, im_gray.channels)
        #perform canny edge detection
        cv.Canny(im_gray, im_cann, thresh_min, thresh_max, 3)
        #convert to 3 channel RGB to allow QImage conversion
        cv.CvtColor(im_cann, frame, cv.CV_GRAY2RGB)


class DrawColorTrack(QtGui.QImage):
    def __init__(self, frame, thresh_hue):
        super(DrawColorTrack, self).__init__()

        #smooth the source image to reduce color noise 
        smo_frame = cv.CreateImage(cv.GetSize(frame), 8, 3)
        cv.Smooth(frame, smo_frame, cv.CV_GAUSSIAN, 5); 
            
        #convert the image to hsv tracking for improved tracking
        hsv_frame = cv.CreateImage(cv.GetSize(smo_frame), 8, 3) 
        cv.CvtColor(smo_frame, hsv_frame, cv.CV_RGB2HSV)
            
        #segment the image based on hue value thresholding. 
        #the first value of each tuple is a hue value in the range 0-180
        thresholded_frame =  cv.CreateImage(cv.GetSize(hsv_frame), 8, 1)
        cv.InRangeS(hsv_frame, ((thresh_hue-10), 20, 20),
                    (thresh_hue+10, 235, 235), thresholded_frame)
        frame_mat=cv.GetMat(thresholded_frame)

        #determine the objects moments and size
        moments = cv.Moments(frame_mat, 0)
        area = cv.GetCentralMoment(moments, 0, 0)
        
        #check that the area is large enough to be our object (linked to image size?)
        if(area > 5000): #cv.GetSize(frame)
            #determine the x and y coordinates of the center of the object 
            #we are tracking by dividing the 1, 0 and 0, 1 moments by the area
            x = int(cv.GetSpatialMoment(moments, 1, 0)/area)
            y = int(cv.GetSpatialMoment(moments, 0, 1)/area)

            #create an overlay to crosshair the center of the tracked object 
            overlay = cv.CreateImage(cv.GetSize(frame), 8, 3) 
            cv.Line(overlay, (0, y), (frame.width, y), cv.CV_RGB(0, 0, 255), 3, 8)
            cv.Line(overlay, (x, 0), (x, frame.height), cv.CV_RGB(0, 0, 255), 3, 8)
            cv.Add(frame, overlay, frame)

            #convert grayscale thresholded image to show counted pixels
            thresholded_frame_RGB =  cv.CreateImage(cv.GetSize(thresholded_frame), 8, 3)
            cv.CvtColor(thresholded_frame, thresholded_frame_RGB, cv.CV_GRAY2RGB)
            cv.Add(frame, thresholded_frame_RGB, frame)


class PySideCam(QtGui.QWidget):
    
    def __init__(self):
        super(PySideCam, self).__init__()
        
        self.initUI()
        
    def initUI(self):

        dimx = 820
        dimy = 520
        self.thresh_min = 10
        self.thresh_max = 100
        self.thresh_hue = 130
        
        self.setGeometry(300, 300, dimx, dimy)
        self.setWindowTitle('PySideCV')
        self.setWindowIcon(QtGui.QIcon('web.png'))

        self.chkboxCanny = QtGui.QCheckBox("Show Canny", self)
        self.chkboxCanny.toggle()
        self.chkboxCanny.setCheckState( Qt.Unchecked )

        self.sliderMin = QtGui.QSlider(Qt.Horizontal, self)
        self.sliderMin.setRange(0, 75)
        self.sliderMin.setValue(10)
        self.sliderMin.sliderReleased.connect(self.sliderMoved)

        setMin = QtGui.QLabel('Minimum threshold')
        
        self.sliderMax = QtGui.QSlider(Qt.Horizontal, self)
        self.sliderMax.setRange(76, 300)
        self.sliderMax.setValue(100)
        self.sliderMax.sliderReleased.connect(self.sliderMoved)

        setMax = QtGui.QLabel('Maximum threshold')

        self.chkboxColorTrack = QtGui.QCheckBox("Track Color", self)
        self.chkboxColorTrack.toggle()
        self.chkboxColorTrack.setCheckState( Qt.Unchecked )

        setHue = QtGui.QLabel('Set Hue')

        self.sliderHue = QtGui.QSlider(Qt.Horizontal, self)
        self.sliderHue.setRange(10, 170)
        self.sliderHue.setValue(90)
        self.sliderHue.sliderReleased.connect(self.sliderMoved)

        vgrid = QtGui.QGridLayout()
        vgrid.addWidget(self.chkboxCanny)
        vgrid.addWidget(setMin)
        vgrid.addWidget(self.sliderMin)
        vgrid.addWidget(setMax)
        vgrid.addWidget(self.sliderMax)
        vgrid.addWidget(self.chkboxColorTrack)
        vgrid.addWidget(setHue)
        vgrid.addWidget(self.sliderHue)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addLayout(vgrid)
        self.setLayout(hbox)

        self.show()
    
        
    def paintEvent(self, event=None):
        
        qp = QtGui.QPainter()

        qp.begin(self)
        self.drawFrames(qp)
        qp.end()

        self.update()
        
    def drawFrames(self, qp):
        #capture frame
        BGR_frame = cv.QueryFrame(camcapture) 

        #OpenCV uses BGR format by default, convert to RGB
        frame = cv.CreateImage(cv.GetSize(BGR_frame), 8, 3)
        cv.CvtColor(BGR_frame, frame, cv.CV_BGR2RGB)
        
        #perform Canny if selected
        if QtGui.QAbstractButton.isChecked(self.chkboxCanny): 
            DrawCanny(frame, self.thresh_min, self.thresh_max)

        #track color if selected
        if QtGui.QAbstractButton.isChecked(self.chkboxColorTrack):
            DrawColorTrack(frame, self.thresh_hue)
        
        #convert to QImage
        qimage = OpenCVQImage(frame) 
        qp.drawImage(QPoint(20, 20), qimage)

    def sliderMoved(self):

        self.thresh_min = self.sliderMin.value()
        self.thresh_max = self.sliderMax.value()
        self.thresh_hue = self.sliderHue.value()

def main():
    
    app = QtGui.QApplication(sys.argv)
    ex = PySideCam()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
