from PyQt5.QtCore import Qt, QTimer, QSize, QTimer, QRect, QPoint
from PyQt5.QtWidgets import QVBoxLayout, QGraphicsOpacityEffect, QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy
from threading import Thread
import os
import asyncio
from PyQt5.QtGui import QColor, QPainter,QMovie, QIcon, QPixmap
import sys
import asyncio
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager
from winrt.windows.storage.streams import DataReader

username = os.getlogin()

class MeidaPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.title = self.c_session_info()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('RaM-MediaX')
        self.setGeometry(300, 300, 700, 360)

        self.media_timer = QTimer(self)
        self.media_timer.timeout.connect(self.update_media)
        self.media_timer.start(1000)

        self.image_timer = QTimer(self)
        self.image_timer.timeout.connect(self.pix)
        self.image_timer.start(1000)


        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.get_image)
        self.save_timer.start(100)

        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self.check_media_session)
        self.session_timer.start(1000)

        with open('style.css', 'r') as file:
            self.css = file.read()

        self.setObjectName('window')
        self.setStyleSheet(self.css)

        self.loadConf()
        self.setup_media_player()

        self.set_opacity()


        window_width = self.width()
        window_height = self.height()

        label_width = self.media_image.width()
        label_height = self.media_image.height()

        x = (window_width - label_width) // 2
        y = (window_height - label_height) // 2

        self.media_image.move(x, y)


    def loadConf(self):
        with open('config.conf', 'r') as file:
            lines = file.readlines()

        config_dict = {}
        for line in lines:
            if line.strip() and not line.startswith('#'):
                key, value = line.split('=', 1)
                config_dict[key.strip()] = value.strip()

        self.opacity = config_dict.get('opacity')
        self.color = config_dict.get('color')
        self.radius_ = config_dict.get('borderRadius')

    def set_opacity(self):
        self.eff = QGraphicsOpacityEffect()
        self.eff.setOpacity(float(self.opacity))    
        self.setGraphicsEffect(self.eff)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(int(self.color[0:2]), int(self.color[4:6]), int(self.color[8:10])))
        painter.drawRoundedRect(self.rect(), int(self.radius_[0:2]), int(self.radius_[4:6]))


    def mousePressEvent(self, event):
        self.oldpos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldpos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldpos = event.globalPos()


    def screen_(self, position: list):
        x = int(self.width() * position[0])
        y = int(self.height() * position[1])
        return x, y

    async def get_media_session(self):
        session_manager = await MediaManager.request_async()
        session = session_manager.get_current_session()
        
        if session:
            print("Session retrieved successfully.")
            print("Available methods in session:", dir(session))
        else:
            print("No media session available.")
        return session


    def play_pause(self):
        async def get_session():
            try:
                session_manager = await MediaManager.request_async()
                current_session = session_manager.get_current_session()
                return await current_session.try_toggle_play_pause_async()
            except AttributeError:
                pass

        pause_play = asyncio.run(get_session())
        return pause_play

    def c_session_info(self):
        async def get_info():
            session_manager = await MediaManager.request_async()
            current_session = session_manager.get_current_session()

            try:
                info = await current_session.try_get_media_properties_async()
                title = info.title
                artist = info.artist
                return f"Now Playing: {title} by {artist}"

            except Exception as e:
                return "No active media session to control."

        session = asyncio.run(get_info())
        return session


    async def control_media(self):
        session_manager = await MediaManager.request_async()
        current_session = session_manager.get_current_session()

        if not current_session:
            return "No active media session to control."

        try:
            info = await current_session.try_get_media_properties_async()
            thumbnail = info.thumbnail


            if thumbnail:
                await self.save_thumbnail(thumbnail, "thumbnail.jpg")

        except Exception as e:
            return ""

    async def save_thumbnail(self, thumbnail, filename, directory=fr"C:\Users\{username}\AppData\Local\Temp"):
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
                filepath = os.path.join(directory, filename)
            else:
                filepath = filename

            stream = await thumbnail.open_read_async()

            input_stream = stream.get_input_stream_at(0)
            data_reader = DataReader(input_stream)
            data_reader.load_async(stream.size)

            data = data_reader.read_bytes(stream.size)
            data_reader.detach_stream()

            with open(filepath, "wb") as file:
                file.write(bytes(data))

        except Exception as e:
            return ""

    async def fast_forward(self):
        session = await self.get_media_session()
        if not session:
            print("⚠️ No active media session")
            return

        try:
            timeline = session.get_timeline_properties()
            
            current_ticks = timeline.position.duration
            max_ticks = timeline.max_seek_time.duration

            if max_ticks <= 0:
                print("❌ Seeking not supported")
                return

            success = await session.try_change_playback_position_async(current_ticks + 1e+8)

            
            if success:
                print("⏩ Fast forwarded 10s")
            else:
                print("❌ Fast forward failed (app rejected the request)")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        os.system('cls')



    async def rewind(self):
        session = await self.get_media_session()
        if not session:
            print("⚠️ No active media session")
            return

        try:
            timeline = session.get_timeline_properties()
            
            current_ticks = timeline.position.duration
            max_ticks = timeline.max_seek_time.duration

            if max_ticks <= 0:
                print("❌ Seeking not supported")
                return

            success = await session.try_change_playback_position_async(current_ticks - 1e+8)

            
            if success:
                print("⏩ Fast forwarded 10s")
            else:
                print("❌ Fast forward failed (app rejected the request)")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        os.system('cls')


    def rewind_action(self):
        async def rewind_action_():
            await self.rewind()

        return asyncio.run(rewind_action_())
    
    def fast_forward_action(self):
        async def fast_forward_action_():
            await self.fast_forward()

        return asyncio.run(fast_forward_action_())

    def get_image(self):
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.control_media(), self.loop)
        else:
            print("Loop not available yet.")

    def update_media(self):
        title = self.c_session_info()
        self.media_label.setText(title)

    def check_media_session(self):
        current_session = self.c_session_info()
        
        if current_session == "No active media session to control.":
            self.media_button.setIcon(QIcon("svgs/play.svg"))
            try:
                self.media_button.clicked.disconnect()
            except TypeError:
                pass
        else:
            try:
                self.media_button.clicked.disconnect()
            except TypeError:
                pass
            self.media_button.clicked.connect(self.toggle_icon)

    def pix(self):
        pixmap = QPixmap(fr"c:\Users\{username}\AppData\Local\Temp\thumbnail.jpg")
        pixmap = pixmap.scaled(250, 100, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        mask = QPixmap(pixmap.size())
        mask.fill(Qt.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.white)
        painter.setPen(Qt.transparent)
        rect = QRect(0, 0, pixmap.width(), pixmap.height())
        painter.drawRoundedRect(rect, 20, 20)
        painter.end()

        pixmap.setMask(mask.createHeuristicMask())

        current_session = self.c_session_info()

        if current_session != "No active media session to control.":
            self.media_image.setPixmap(pixmap)
        else:
            blank_pixmap = QPixmap(self.media_image.size())
            blank_pixmap.fill(Qt.transparent)

            painter = QPainter(blank_pixmap)
            painter.setPen(QColor("gray"))
            painter.drawText(blank_pixmap.rect(), Qt.AlignCenter, "No Media")
            painter.end()

            self.media_image.setPixmap(blank_pixmap)

        return pixmap

    def toggle_icon(self):
        if self.is_playing:
            self.media_button.setIcon(QIcon("svgs/play.svg"))
        else:
            self.media_button.setIcon(QIcon("svgs/pause.svg"))
        self.is_playing = not self.is_playing


        self.play_pause()

    def setup_media_player(self):
        self.media_label = QLabel(self.title, self)
        self.media_label.setWordWrap(True)
        self.media_label.setObjectName('title')
        self.media_label.setStyleSheet(self.css)

        hbox_layout = QHBoxLayout()
        hbox_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hbox_layout.addWidget(self.media_label)
        hbox_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hbox_layout.setContentsMargins(10, 0, 10, 0)
        hbox_layout.setSpacing(15)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(0)
        outer_layout.addLayout(hbox_layout)
        outer_layout.addStretch()

        self.setLayout(outer_layout)

        # self.setLayout(outer_layout)

        self.media_button = QPushButton(self)
        self.media_button.setIcon(QIcon('svgs/play.svg'))
        self.media_button.setFixedSize(30, 30)
        self.media_button.setIconSize(QSize(30, 30))
        self.media_button.setObjectName('playPause')
        self.media_button.setStyleSheet(self.css)
        x, y = self.screen_([0.48, 0.72])
        self.media_button.move(x, y)
        self.media_button.clicked.connect(self.toggle_icon)
        self.is_playing = False

        self.media_image = QLabel(self)
        self.media_image.setPixmap(self.pix())
        self.media_image.setScaledContents(True)
        self.media_image.setFixedSize(250, 150)
        self.media_image.setAlignment(Qt.AlignCenter)

        self.close_button = QPushButton("", self)
        self.close_button.clicked.connect(self.close_app)
        self.close_button.setFixedSize(40, 40)
        self.close_button.setIconSize(QSize(40, 40))
        self.close_button.setObjectName('Close')
        self.close_button.setStyleSheet(self.css)

        x, y = self.screen_([0.92, 0.04])
        self.close_button.move(x, y)

        self.minimize_button = QPushButton("", self)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.setFixedSize(40, 40)
        self.minimize_button.setIconSize(QSize(40, 40))
        self.minimize_button.setObjectName("miniMize")
        self.minimize_button.setStyleSheet(self.css)
        x, y = self.screen_([0.02, 0.04])
        self.minimize_button.move(x, y)

        self.forward = QPushButton("", self)
        self.forward.setIcon(QIcon('images/forward.png'))
        self.forward.clicked.connect(self.fast_forward_action)
        self.forward.setFixedSize(33, 33)
        self.forward.setIconSize(QSize(33, 33))
        self.forward.setObjectName('Forward')
        self.forward.setStyleSheet(self.css)
        x, y = self.screen_([0.62, 0.72])
        self.forward.move(x, y)

        self.rewind_ = QPushButton("", self)
        self.rewind_.setIcon(QIcon('images/rewind.png'))
        self.rewind_.clicked.connect(self.rewind_action)
        self.rewind_.setFixedSize(33, 33)
        self.rewind_.setIconSize(QSize(33, 33))
        self.rewind_.setObjectName('Rewind')
        self.rewind_.setStyleSheet(self.css)
        x, y = self.screen_([0.325, 0.72])
        self.rewind_.move(x, y)

        self.movie = QMovie("gifs/close.gif")
        self.movie.frameChanged.connect(self.update_icon)
        self.movie.start()

        self.movie_ = QMovie('gifs/minimize.gif')
        self.movie_.frameChanged.connect(self.update_minimize)
        self.movie_.start()

    def update_icon(self):
        self.close_button.setIcon(QIcon(self.movie.currentPixmap()))

    def update_minimize(self):
        self.minimize_button.setIcon(QIcon(self.movie_.currentPixmap()))

    def close_app(self):
        sys.exit()

def start_asyncio_loop(panel):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    panel.loop = loop
    loop.run_forever()

def run_loop():
    app = QApplication([])
    app.setWindowIcon(QIcon('images/media_player.png'))
    # app.setWindowTitl
    side = MeidaPlayer()
    
    Thread(target=start_asyncio_loop, args=(side,), daemon=True).start()

    side.show()
    app.exec_()

run_loop()