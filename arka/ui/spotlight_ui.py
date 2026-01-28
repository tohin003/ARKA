
import sys
import threading
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QVBoxLayout, 
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QGuiApplication

from arka.core.orchestrator import Orchestrator
from arka.vision.screen_watcher import get_screen_watcher

class SpotlightUI(QMainWindow):
    """
    Hovering text box overlay for ARKA agent.
    Acts like macOS Spotlight / Arc Search.
    """
    
    # Signals to communicate with worker threads
    response_ready = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        self.orchestrator = Orchestrator()
        self.watcher = get_screen_watcher()
        self.is_processing = False
        
        self._init_ui()
        self._setup_styles()
        
        # Center on screen
        self._center_on_screen()
        
    def _init_ui(self):
        """Initialize the UI components."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Background frame with rounded corners
        self.frame = QFrame()
        self.frame.setObjectName("MainFrame")
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(15, 15, 15, 15)
        
        # Input Area
        self.input_layout = QHBoxLayout()
        
        # AI Icon
        self.icon_label = QLabel("✨")
        self.icon_label.setFont(QFont("SF Pro Display", 24))
        self.input_layout.addWidget(self.icon_label)
        
        # Text Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask ARKA or assign a task...")
        self.input_field.setFont(QFont("SF Pro Display", 18))
        self.input_field.returnPressed.connect(self.process_input)
        self.input_layout.addWidget(self.input_field)
        
        self.frame_layout.addLayout(self.input_layout)
        
        # Response Area (Hidden by default)
        self.response_label = QLabel("")
        self.response_label.setObjectName("ResponseLabel")
        self.response_label.setWordWrap(True)
        self.response_label.setFont(QFont("SF Pro Text", 14))
        self.response_label.hide()
        self.frame_layout.addWidget(self.response_label)
        
        # Status Bar
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")
        self.status_layout.addWidget(self.status_label)
        
        self.status_layout.addStretch()
        
        # Action Buttons
        self.attach_btn = QPushButton("📷 Attach Screen")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self.attach_screen)
        self.status_layout.addWidget(self.attach_btn)
        
        self.close_btn = QPushButton("Esc")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        self.status_layout.addWidget(self.close_btn)
        
        self.frame_layout.addLayout(self.status_layout)
        
        self.layout.addWidget(self.frame)
        
        # Resize constraint
        self.setFixedWidth(600)
    
    def _setup_styles(self):
        """Apply CSS styling."""
        self.setStyleSheet("""
            #MainFrame {
                background-color: rgba(30, 30, 35, 0.95);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                selection-background-color: #007AFF;
            }
            #ResponseLabel {
                color: #E0E0E0;
                padding-top: 10px;
                background: transparent;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                margin-top: 10px;
            }
            #StatusLabel {
                color: #888888;
                font-size: 12px;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        
    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - 400) // 2  # Slightly above center
        self.move(x, y)
        
    def attach_screen(self):
        """Capture screen context."""
        self.status_label.setText("Analyzing current screen...")
        # In a real scenario, this would capture a frame and pass it to the orchestrator context
        self.input_field.setPlaceholderText("Ask about this screen...")
        
    def process_input(self):
        """Send input to agent."""
        text = self.input_field.text()
        if not text:
            return
            
        self.is_processing = True
        self.input_field.setDisabled(True)
        self.status_label.setText("Thinking...")
        self.response_label.setText("")
        self.response_label.hide()
        
        # Run in background thread
        threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()
        
    def _run_agent(self, text: str):
        """Run agent logic in background."""
        try:
            # Check for visual context
            if "screen" in text.lower() or "this" in text.lower():
                # self.watcher.capture_frame() # Optional: grab fresh frame
                pass
                
            response = self.orchestrator.chat(text, use_agents=True)
            self.response_ready.emit(response)
            
        except Exception as e:
            self.response_ready.emit(f"Error: {str(e)}")
            
    def display_response(self, text: str):
        """Update UI with response."""
        self.response_label.setText(text)
        self.response_label.show()
        self.input_field.setDisabled(False)
        self.input_field.setFocus()
        self.status_label.setText("Ready")
        self.adjustSize()
        self.is_processing = False
        
        # Bind signal
        self.response_ready.connect(self.display_response)

def main():
    app = QApplication(sys.argv)
    
    # Hide dock icon if possible (requires Info.plist or specific flags)
    
    window = SpotlightUI()
    window.show()
    window.activateWindow()
    window.raise_()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
