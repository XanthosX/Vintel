from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QPoint,pyqtSignal, QUrl, QEvent

class WebEnginePage(QWebEnginePage):
    mapLinkClicked = pyqtSignal(QUrl) 
    def acceptNavigationRequest(self, url, type, isMainFrame):
        if type == QWebEnginePage.NavigationTypeLinkClicked:
            self.mapLinkClicked.emit(url)
            return False
        return True
    def javaScriptConsoleMessage(self, level, msg, line, source):
        # supress Javascript warnings and uncaught ReferenceError exceptions for JS functions
        pass
		
class PanningWebView(QWebEngineView):
  
    def setPage(self, newPage):
        super(PanningWebView, self).setPage(newPage)
        self.widget = self.page()

    def __init__(self, parent=None):
        super(PanningWebView, self).__init__()
        self.pressed = False
        self.scrolling = False
        self.ignored = []
        self.position = None
        self.offset = 0
        self.handIsClosed = False
        self.clickedInScrollBar = False
        self.setPage(WebEnginePage(self))

    def mousePressEvent(self, mouseEvent):
        pos = mouseEvent.pos()

        if self.pointInScroller(pos, QtCore.Qt.Vertical) or self.pointInScroller(pos, QtCore.Qt.Horizontal):
            self.clickedInScrollBar = True
        else:
            if self.ignored.count(mouseEvent):
                self.ignored.remove(mouseEvent)
                return QWebEngineView.mousePressEvent(self, mouseEvent)

            if not self.pressed and not self.scrolling and mouseEvent.modifiers() == QtCore.Qt.NoModifier:
                if mouseEvent.buttons() == QtCore.Qt.LeftButton:
                    self.pressed = True
                    self.scrolling = False
                    self.handIsClosed = False
                    QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)

                    self.position = mouseEvent.pos()
                    frame = self.page().mainFrame()
                    xTuple = frame.evaluateJavaScript("window.scrollX").toInt()
                    yTuple = frame.evaluateJavaScript("window.scrollY").toInt()
                    self.offset = QPoint(xTuple[0], yTuple[0])
                    return

        return QWebEngineView.mousePressEvent(self, mouseEvent)


    def mouseReleaseEvent(self, mouseEvent):
        if self.clickedInScrollBar:
            self.clickedInScrollBar = False
        else:
            if self.ignored.count(mouseEvent):
                self.ignored.remove(mouseEvent)
                return QWebEngineView.mousePressEvent(self, mouseEvent)

            if self.scrolling:
                self.pressed = False
                self.scrolling = False
                self.handIsClosed = False
                QApplication.restoreOverrideCursor()
                return

            if self.pressed:
                self.pressed = False
                self.scrolling = False
                self.handIsClosed = False
                QApplication.restoreOverrideCursor()

                event1 = QMouseEvent(QEvent.MouseButtonPress, self.position, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                event2 = QMouseEvent(mouseEvent)
                self.ignored.append(event1)
                self.ignored.append(event2)
                QApplication.postEvent(self, event1)
                QApplication.postEvent(self, event2)
                return
        return QWebEngineView.mouseReleaseEvent(self, mouseEvent)


    def mouseMoveEvent(self, mouseEvent):
        if not self.clickedInScrollBar:
            if self.scrolling:
                if not self.handIsClosed:
                    QApplication.restoreOverrideCursor()
                    QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)
                    self.handIsClosed = True
                delta = mouseEvent.pos() - self.position
                p = self.offset - delta
                frame = self.page().mainFrame()
                frame.evaluateJavaScript(QString("window.scrollTo(%1, %2);").arg(p.x()).arg(p.y()));
                return

            if self.pressed:
                self.pressed = False
                self.scrolling = True
                return
        return QWebEngineView.mouseMoveEvent(self, mouseEvent)


    def pointInScroller(self, position, orientation):
        rect = self.page().mainFrame().scrollBarGeometry(orientation)
        leftTop = self.mapToGlobal(QtCore.QPoint(rect.left(), rect.top()))
        rightBottom = self.mapToGlobal(QtCore.QPoint(rect.right(), rect.bottom()))
        globalRect = QtCore.QRect(leftTop.x(), leftTop.y(), rightBottom.x(), rightBottom.y())
        return globalRect.contains(self.mapToGlobal(position))
