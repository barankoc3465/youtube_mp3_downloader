import os
import re
import sys
import static_ffmpeg
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from yt_dlp import YoutubeDL

# Sanal ortam içerisine FFmpeg binary dosyalarını hazırlar
static_ffmpeg.add_paths()


class DownloadWorker(QThread):
    progress_signal = Signal(str, int)
    finished_signal = Signal(bool, str)

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    def download_progress_hook(self, d):
        if d['status'] == 'downloading':
            filename = os.path.basename(d.get('filename', ''))
            percent = d.get('_percent_str', '').strip()
            match = re.search(r'(\d+(?:\.\d+)?)', percent)
            progress = min(99, int(float(match.group(1)))) if match else 0
            self.progress_signal.emit(
                f'İndiriliyor  •  {percent}  •  {filename[:36]}...',
                progress,
            )
        elif d['status'] == 'finished':
            self.progress_signal.emit('MP3 formatına dönüştürülüyor...', 100)

    def run(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # Oynatma listesi adıyla klasör açıp MP3'leri içine kaydeder
            'outtmpl': os.path.join(
                self.save_path, '%(playlist_title)s/%(title)s.%(ext)s'
            ),
            'progress_hooks': [self.download_progress_hook],
            'ignoreerrors': True,
            'quiet': True,
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished_signal.emit(True, 'İndirme tamamlandı!')
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class DownloaderApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouTube Oynatma Listesi MP3 İndirici')
        self.setMinimumSize(620, 480)
        self.resize(680, 520)

        self.default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: #f5f7fb;
                color: #1f2937;
                font-size: 14px;
            }
            QFrame#card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }
            QLabel#title {
                color: #111827;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#subtitle, QLabel#hint {
                color: #6b7280;
            }
            QLabel#section {
                color: #374151;
                font-size: 13px;
                font-weight: 700;
            }
            QLineEdit {
                background: #f9fafb;
                border: 1px solid #d1d5db;
                border-radius: 9px;
                padding: 11px 12px;
                selection-background-color: #4f46e5;
            }
            QLineEdit:focus {
                background: white;
                border: 2px solid #6366f1;
                padding: 10px 11px;
            }
            QPushButton {
                border: none;
                border-radius: 9px;
                padding: 11px 18px;
                font-weight: 600;
            }
            QPushButton#browse {
                background: #eef2ff;
                color: #4338ca;
            }
            QPushButton#browse:hover {
                background: #e0e7ff;
            }
            QPushButton#download {
                background: #4f46e5;
                color: white;
                font-size: 15px;
                padding: 14px;
            }
            QPushButton#download:hover {
                background: #4338ca;
            }
            QPushButton#download:disabled {
                background: #a5b4fc;
            }
            QProgressBar {
                background: #eef2ff;
                border: none;
                border-radius: 5px;
                min-height: 10px;
                max-height: 10px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #6366f1;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)

        header = QVBoxLayout()
        header.setSpacing(5)
        title = QLabel("Oynatma listesinden MP3 indir")
        title.setObjectName('title')
        subtitle = QLabel('Favori müziklerinizi kolayca bilgisayarınıza kaydedin.')
        subtitle.setObjectName('subtitle')
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        card = QFrame()
        card.setObjectName('card')
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 22)
        card_layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        url_label = QLabel('Oynatma listesi bağlantısı')
        url_label.setObjectName('section')
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            'https://www.youtube.com/playlist?list=...'
        )
        self.url_input.setClearButtonEnabled(True)
        form_layout.addRow(url_label, self.url_input)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        self.path_input = QLineEdit(self.default_dir)
        self.path_input.setClearButtonEnabled(True)
        self.browse_btn = QPushButton('Gözat...')
        self.browse_btn.setObjectName('browse')
        self.browse_btn.clicked.connect(self.select_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)

        path_label = QLabel('Kayıt klasörü')
        path_label.setObjectName('section')
        form_layout.addRow(path_label, path_layout)
        card_layout.addLayout(form_layout)

        self.download_btn = QPushButton('MP3 Olarak İndir')
        self.download_btn.setObjectName('download')
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setDefault(True)
        card_layout.addWidget(self.download_btn)
        layout.addWidget(card)

        status_card = QFrame()
        status_card.setObjectName('card')
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(22, 18, 22, 18)
        status_layout.setSpacing(10)

        status_header = QHBoxLayout()
        self.status_indicator = QLabel('●')
        self.status_indicator.setStyleSheet('color: #10b981; font-size: 18px;')
        self.status_label = QLabel('Hazır — bağlantıyı yapıştırıp başlayabilirsiniz.')
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        status_header.addWidget(self.status_indicator)
        status_header.addWidget(self.status_label)
        status_layout.addLayout(status_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)

        hint = QLabel('Dosyalar, seçtiğiniz klasörde oynatma listesi adına göre düzenlenir.')
        hint.setObjectName('hint')
        status_layout.addWidget(hint)
        layout.addWidget(status_card)
        layout.addStretch()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Klasör Seç', self.path_input.text()
        )
        if folder:
            self.path_input.setText(folder)

    def start_download(self):
        url = self.url_input.text().strip()
        save_path = self.path_input.text().strip()
        if not url or not re.match(r'https?://', url):
            QMessageBox.warning(
                self, 'Bağlantı gerekli',
                'Lütfen http:// veya https:// ile başlayan geçerli bir YouTube linki girin.',
            )
            return
        if not save_path or not os.path.isdir(save_path):
            QMessageBox.warning(
                self, 'Klasör gerekli',
                'Lütfen geçerli bir kayıt klasörü seçin.'
            )
            return

        self.download_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_indicator.setStyleSheet('color: #f59e0b; font-size: 18px;')
        self.status_label.setText('İndirme başlatılıyor...')

        self.worker = DownloadWorker(url, save_path)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, message, progress):
        self.status_label.setText(message)
        self.progress_bar.setValue(progress)

    def on_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        if success:
            self.status_label.setText('Tamamlandı!')
            self.status_indicator.setStyleSheet('color: #10b981; font-size: 18px;')
            self.progress_bar.setValue(100)
            QMessageBox.information(
                self,
                'Başarılı',
                f'Oynatma listesindeki tüm MP3\'ler indirildi:\n{self.path_input.text()}',
            )
        else:
            self.status_label.setText('Hata oluştu.')
            self.status_indicator.setStyleSheet('color: #ef4444; font-size: 18px;')
            QMessageBox.critical(self, 'Hata', f'Bir hata oluştu:\n{message}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec())