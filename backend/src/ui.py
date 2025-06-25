import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QFrame,
    QFileDialog,
)
from PyQt5.QtGui import QImage, QPainter, QColor, QPixmap, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal #QBuffer, QIODevice
import base64
import requests
from utils import *
from PyQt5.QtGui import QPainter, QImage, QColor, QPen
from config import endpoint_config


class GenerateTexturesWorker(QThread):
    result = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, img_bytes, mask_bytes, prompt):
        super().__init__()
        self.img_bytes = img_bytes
        self.mask_bytes = mask_bytes
        self.prompt = prompt

    def run(self):
        request_body = {
            "user_image": self.img_bytes,
            "user_mask": self.mask_bytes,
            "prompt": self.prompt,
            "batch": False,
        }
        url = f"http://{endpoint_config.host}:{endpoint_config.port}{endpoint_config.endpoint}"
        log_to_file.log("info", f"Requesting textures from {url}")
        try:
            response = requests.post(
                url,
                json=request_body,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 200:
                images = response.json()
                self.result.emit(images)
            else:
                self.error.emit(response.text)
        except Exception as e:
            self.error.emit(str(e))


class BrushWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.brush_size = 10
        self.setFixedSize(512, 512)
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.mask = QImage(self.size(), QImage.Format_Grayscale8)
        self.mask.fill(Qt.black)
        self.overlay = QImage(self.size(), QImage.Format_ARGB32)
        self.overlay.fill(Qt.transparent)
        self.last_mouse_pos = None

    def enterEvent(self, event):
        self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, self.image)
        painter.drawImage(0, 0, self.overlay)
        if self.last_mouse_pos:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.last_mouse_pos, self.brush_size, self.brush_size)

    def mouseMoveEvent(self, event):
        self.last_mouse_pos = event.pos()
        self.update()
        if event.buttons() & Qt.LeftButton:
            self.paint_on_canvas(event.pos())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            self.paint_on_canvas(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.last_mouse_pos = None
        self.update()

    def paint_on_canvas(self, pos):
        painter = QPainter(self.overlay)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawEllipse(pos, self.brush_size, self.brush_size)
        mask_painter = QPainter(self.mask)
        mask_painter.setPen(Qt.NoPen)
        mask_painter.setBrush(QColor(255, 255, 255))
        mask_painter.drawEllipse(pos, self.brush_size, self.brush_size)
        self.update()

    def get_mask(self):
        return self.mask

    def setBrushSize(self, size):
        self.brush_size = size


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Texture Generation Tool")
        self.setGeometry(100, 100, 1000, 600)
        self.initUI()
        apply_stylesheet(self)
        self.original_image = None

    def initUI(self):
        left_panel = QWidget(self)
        left_layout = QVBoxLayout()
        self.canvas = BrushWidget()
        left_layout.addWidget(self.canvas)
        brush_size_slider = QSlider(Qt.Horizontal)
        brush_size_slider.setRange(1, 50)
        brush_size_slider.setValue(10)
        brush_size_slider.valueChanged.connect(self.adjustBrushSize)
        left_layout.addWidget(QLabel("Adjust Brush Size"))
        left_layout.addWidget(brush_size_slider)
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Enter your prompt...")
        left_layout.addWidget(self.prompt_input)
        left_panel.setLayout(left_layout)
        right_panel = QWidget(self)
        right_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        right_panel.setLayout(right_layout)
        load_button = QPushButton("Load Image")
        load_button.clicked.connect(self.loadImage)
        left_layout.addWidget(load_button)
        generate_button = QPushButton("Generate Textures")
        generate_button.clicked.connect(self.generateTextures)
        left_layout.addWidget(generate_button)
        main_layout = QHBoxLayout()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def createTabs(self):
        self.tabs.addTab(QFrame(), "Albedo")
        self.tabs.addTab(QFrame(), "Normal")
        self.tabs.addTab(QFrame(), "Roughness")
        self.tabs.addTab(QFrame(), "Metallic")
        self.tabs.addTab(QFrame(), "Height")
        self.tabs.addTab(QFrame(), "AO")
        self.tabs.addTab(QFrame(), "Specular")

    def destroyTabs(self):
        if hasattr(self, "tabs") and self.tabs:
            while self.tabs.count() > 0:
                self.tabs.removeTab(0)

    def resetCanvas(self):
        self.canvas.image.fill(Qt.white)
        self.canvas.mask.fill(Qt.black)
        self.canvas.overlay.fill(Qt.transparent)
        self.canvas.update()

    def loadImage(self):
        self.resetGUI()
        file, _ = QFileDialog.getOpenFileName(self, "Open Image File")
        if file:
            self.original_image = QImage(file)
            self.canvas.image = self.original_image.scaled(
                self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.canvas.update()

    def resetGUI(self):
        self.resetCanvas()
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
        self.createTabs()

    def adjustBrushSize(self, size):
        self.canvas.setBrushSize(size)

    def populateTabs(self, images):
        for map_name, image_base64 in images.items():
            # Decode the base64 string back into image bytes
            image_bytes = base64.b64decode(image_base64)
            # Convert the image bytes to a QImage
            qimage = QImage.fromData(image_bytes, "PNG")
            pixmap = QPixmap.fromImage(qimage)
            label = QLabel()
            label.setPixmap(pixmap)
            index = self.tabs.indexOf(
                self.tabs.findChild(QFrame, map_name.capitalize())
            )
            if index != -1:
                self.tabs.widget(index).layout().addWidget(label)
            else:
                frame = QFrame()
                layout = QVBoxLayout()
                layout.addWidget(label)
                frame.setLayout(layout)
                self.tabs.addTab(frame, map_name.capitalize())

    def generateTextures(self):
        self.destroyTabs()
        if not self.original_image:
            print("No image loaded.")
            return
        user_mask = self.canvas.get_mask()
        user_mask.save("./output/mask.png", "PNG")
        prompt = self.prompt_input.text()
        if not prompt:
            print("Please enter a prompt.")
            return
        # img_buffer = QBuffer()
        # img_buffer.open(QIODevice.WriteOnly)
        # self.original_image.save(img_buffer, "PNG")
        # img_bytes = img_buffer.data()
        # mask_buffer = QBuffer()
        # mask_buffer.open(QIODevice.WriteOnly)
        # user_mask.save(mask_buffer, "PNG")
        # mask_bytes = mask_buffer.data()
        self.worker = GenerateTexturesWorker(
            qimage_to_base64(self.original_image),
            qimage_to_base64(user_mask),
            prompt)
        self.worker.result.connect(self.populateTabs)
        self.worker.error.connect(self.showError)
        self.worker.start()

    def showError(self, error_message):
        print("Error generating textures:", error_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
