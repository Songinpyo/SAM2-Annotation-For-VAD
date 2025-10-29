import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QSlider, QSpinBox, QRadioButton,
    QButtonGroup, QScrollArea, QSplitter, QMessageBox, QLineEdit,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage, QKeySequence
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem, QShortcut
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.utils import load_config
from core.dataset.ucf_crime import UCFCrimeAdapter
from core.dataset.xd_violence import XDViolenceAdapter
from core.eis.dt_select import select_dt_auto
from core.eis.anchors import generate_anchors, subsample_anchors, pad_anchors
from core.io.video import VideoLoader
from core.io.export import export_annotations, validate_annotations, generate_statistics
from core.io.import_txt import import_annotations
from core.io.paths import get_video_path, get_annotation_path
from core.annotation.state import AnnotationState


class AnnotationListWidget(QListWidget):
    """Custom QListWidget with Delete key support"""

    delete_requested = pyqtSignal()

    def keyPressEvent(self, event):
        """Handle Delete/Backspace key"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class CanvasViewer(QGraphicsView):
    """Interactive canvas for drawing bboxes and points"""

    # Signal emitted when drawing is completed
    drawing_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = None
        self.drawing_mode = 'bbox'  # bbox, pos_point, neg_point
        self.stroke_color = QColor('#FF0000')

        self.start_pos = None
        self.current_rect = None
        self.current_point = None

        self.scale_x = 1.0
        self.scale_y = 1.0
        self.original_width = 1
        self.original_height = 1

    def set_image(self, frame_rgb, target_width=800):
        """Load and display image"""
        self.scene.clear()

        # Reset drawing state
        self.current_rect = None
        self.current_point = None
        self.start_pos = None

        h, w = frame_rgb.shape[:2]
        self.original_width = w
        self.original_height = h

        # Convert to QImage
        bytes_per_line = 3 * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Resize for display
        ratio = target_width / w
        display_width = target_width
        display_height = int(h * ratio)

        self.scale_x = w / display_width
        self.scale_y = h / display_height

        pixmap = QPixmap.fromImage(q_img).scaled(display_width, display_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        self.setSceneRect(0, 0, display_width, display_height)

    def draw_annotations(self, annotations, config):
        """Draw existing annotations on canvas"""
        if not self.pixmap_item:
            return

        for entity_id, data in annotations.items():
            role = entity_id[:-1]
            entity_num = entity_id[-1]
            color_str = config['ui']['colors'].get(role, '#FF0000')
            color = QColor(color_str)

            # Draw bbox
            if data['bbox']:
                x, y, w, h = data['bbox']
                # Scale to display size
                x_disp = x / self.scale_x
                y_disp = y / self.scale_y
                w_disp = w / self.scale_x
                h_disp = h / self.scale_y

                pen = QPen(color, 3)
                rect = self.scene.addRect(x_disp, y_disp, w_disp, h_disp, pen)

                # Draw ID label with bold font
                text = self.scene.addText(entity_num)
                text.setDefaultTextColor(color)
                font = text.font()
                font.setPointSize(14)
                font.setBold(True)
                text.setFont(font)
                text.setPos(x_disp + 5, y_disp + 5)

            # Draw pos points
            pos_color = QColor(config['ui']['colors']['pos_point'])
            for pt in data['pos_points']:
                x, y = pt
                x_disp = x / self.scale_x
                y_disp = y / self.scale_y
                r = 5
                self.scene.addEllipse(x_disp - r, y_disp - r, 2*r, 2*r, QPen(pos_color), QBrush(pos_color))

            # Draw neg points
            neg_color = QColor(config['ui']['colors']['neg_point'])
            for pt in data['neg_points']:
                x, y = pt
                x_disp = x / self.scale_x
                y_disp = y / self.scale_y
                r = 5
                self.scene.addEllipse(x_disp - r, y_disp - r, 2*r, 2*r, QPen(neg_color), QBrush(neg_color))

    def set_drawing_mode(self, mode, color_str):
        """Set drawing mode and color"""
        self.drawing_mode = mode
        self.stroke_color = QColor(color_str)

    def clamp_to_image(self, pos):
        """Clamp position to image boundaries"""
        if not self.pixmap_item:
            return pos

        rect = self.pixmap_item.boundingRect()
        x = max(rect.left(), min(rect.right(), pos.x()))
        y = max(rect.top(), min(rect.bottom(), pos.y()))
        return QPointF(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_item:
            pos = self.mapToScene(event.pos())
            # Clamp to image boundaries
            pos = self.clamp_to_image(pos)
            self.start_pos = pos

            if self.drawing_mode == 'bbox':
                # Clear any previous point
                self.current_point = None
                # Start drawing rectangle
                self.current_rect = self.scene.addRect(
                    pos.x(), pos.y(), 0, 0,
                    QPen(self.stroke_color, 3)
                )
            else:
                # Clear any previous rect
                self.current_rect = None
                # Draw point
                r = 5
                self.current_point = self.scene.addEllipse(
                    pos.x() - r, pos.y() - r, 2*r, 2*r,
                    QPen(self.stroke_color),
                    QBrush(self.stroke_color)
                )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_pos and self.drawing_mode == 'bbox' and self.current_rect:
            pos = self.mapToScene(event.pos())
            # Clamp to image boundaries
            pos = self.clamp_to_image(pos)
            rect = QRectF(self.start_pos, pos).normalized()
            self.current_rect.setRect(rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Emit signal when drawing is completed
            if self.current_rect or self.current_point:
                self.drawing_completed.emit()

            self.start_pos = None

        super().mouseReleaseEvent(event)

    def get_last_drawn_object(self):
        """Get coordinates of last drawn object in original image space"""
        if self.drawing_mode == 'bbox' and self.current_rect:
            rect = self.current_rect.rect()
            x = rect.x() * self.scale_x
            y = rect.y() * self.scale_y
            w = rect.width() * self.scale_x
            h = rect.height() * self.scale_y

            return ('bbox', [x, y, w, h])
        elif self.drawing_mode in ['pos_point', 'neg_point'] and self.current_point:
            rect = self.current_point.rect()
            x = (rect.x() + rect.width()/2) * self.scale_x
            y = (rect.y() + rect.height()/2) * self.scale_y
            return ('point', [x, y])

        return None

    def clear_drawing_state(self):
        """Clear current drawing objects"""
        self.current_rect = None
        self.current_point = None
        self.start_pos = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.config = load_config()
        self.ann_state = AnnotationState()

        self.video_loader = None
        self.current_frame = None
        self.anchors = []
        self.current_adapter = None
        self.current_video = None
        self.timeline_buttons = []  # Store timeline buttons for updating colors

        self.init_ui()
        self.setup_shortcuts()

    def init_ui(self):
        self.setWindowTitle("SAM2 Anomaly Annotation Tool - PyQt5")
        self.setGeometry(100, 100, 1600, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Left panel: Settings
        left_panel = self.create_settings_panel()

        # Right panel: Main area
        right_panel = self.create_main_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def create_settings_panel(self):
        """Create left settings panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Display width
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        display_group.setLayout(display_layout)

        display_layout.addWidget(QLabel("Display Width (px):"))
        self.display_width_slider = QSlider(Qt.Horizontal)
        self.display_width_slider.setMinimum(400)
        self.display_width_slider.setMaximum(1200)
        self.display_width_slider.setValue(800)
        self.display_width_slider.setTickInterval(100)
        self.display_width_slider.setTickPosition(QSlider.TicksBelow)
        self.display_width_slider.valueChanged.connect(self.on_display_width_changed)
        display_layout.addWidget(self.display_width_slider)

        self.display_width_label = QLabel("800")
        display_layout.addWidget(self.display_width_label)

        layout.addWidget(display_group)

        # Dataset selection
        layout.addWidget(QLabel("Dataset:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItem("-- Select Dataset --")
        self.dataset_combo.addItems(["ucf-crime", "xd-violence"])
        self.dataset_combo.currentTextChanged.connect(self.on_dataset_changed)
        layout.addWidget(self.dataset_combo)

        # Video selection
        layout.addWidget(QLabel("Video:"))
        self.video_combo = QComboBox()
        self.video_combo.currentTextChanged.connect(self.on_video_changed)
        layout.addWidget(self.video_combo)

        # Video navigation shortcuts hint
        video_nav_hint = QLabel("Ctrl+A / Ctrl+D: Prev/Next Video")
        video_nav_hint.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        layout.addWidget(video_nav_hint)

        # Dt mode
        layout.addWidget(QLabel("Δt Mode:"))
        self.dt_combo = QComboBox()
        self.dt_combo.addItems(["AUTO", "1s", "2s", "4s", "10s"])
        self.dt_combo.currentTextChanged.connect(self.on_dt_changed)
        layout.addWidget(self.dt_combo)

        # Run name
        layout.addWidget(QLabel("Run Name:"))
        self.run_name_input = QLineEdit("default")
        layout.addWidget(self.run_name_input)
        layout.addWidget(QLabel("Saves to: annotations/<run_name>/<video>.txt"))

        # Import/Export buttons
        self.import_btn = QPushButton("Import Existing Annotation")
        self.import_btn.clicked.connect(self.on_import)
        layout.addWidget(self.import_btn)

        layout.addWidget(QLabel(""))  # Small spacing

        # Export warning message (emphasized)
        export_warning = QLabel("IMPORTANT: Export saves CURRENT video ONLY!\nYou must export EACH video separately!")
        export_warning.setStyleSheet("""
            QLabel {
                color: #FF6B00;
                font-weight: bold;
                background-color: #FFF3E0;
                padding: 8px;
                border: 2px solid #FF6B00;
                border-radius: 4px;
            }
        """)
        export_warning.setWordWrap(True)
        layout.addWidget(export_warning)

        self.export_btn = QPushButton("💾 Export Current Video [Ctrl+S]")
        self.export_btn.clicked.connect(self.on_export)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.export_btn)

        layout.addWidget(QLabel(""))  # Small spacing

        # Entity Notes section
        notes_label = QLabel("Entity Notes (optional):")
        notes_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(notes_label)

        notes_hint = QLabel("Add text notes for current entity")
        notes_hint.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        layout.addWidget(notes_hint)

        self.entity_notes_input = QTextEdit()
        self.entity_notes_input.setMaximumHeight(80)
        self.entity_notes_input.setPlaceholderText("Enter notes for this entity...")
        self.entity_notes_input.textChanged.connect(self.on_entity_note_changed)
        layout.addWidget(self.entity_notes_input)

        layout.addStretch()

        return panel

    def create_main_panel(self):
        """Create right main panel"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Timeline info
        self.timeline_info_label = QLabel("Please select a dataset and video from the left panel to begin")
        self.timeline_info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.timeline_info_label)

        # Timeline buttons (will be populated dynamically)
        self.timeline_widget = QWidget()
        self.timeline_layout = QHBoxLayout()
        self.timeline_widget.setLayout(self.timeline_layout)

        timeline_scroll = QScrollArea()
        timeline_scroll.setWidget(self.timeline_widget)
        timeline_scroll.setWidgetResizable(True)
        timeline_scroll.setMaximumHeight(80)
        layout.addWidget(timeline_scroll)

        # Current frame label
        self.current_frame_label = QLabel("Current Frame: N/A")
        self.current_frame_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.current_frame_label)

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Prev Anchor [A]")
        self.prev_btn.clicked.connect(self.on_prev_anchor)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("Next Anchor ▶ [D]")
        self.next_btn.clicked.connect(self.on_next_anchor)
        nav_layout.addWidget(self.next_btn)

        self.undo_btn = QPushButton("↶ Undo [Ctrl+Z]")
        self.undo_btn.clicked.connect(self.on_undo)
        nav_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↷ Redo [Ctrl+Shift+Z]")
        self.redo_btn.clicked.connect(self.on_redo)
        nav_layout.addWidget(self.redo_btn)

        layout.addLayout(nav_layout)

        # Entity panel
        entity_group = QGroupBox("Entity Panel")
        entity_layout = QHBoxLayout()
        entity_group.setLayout(entity_layout)

        # Role selection
        role_layout = QVBoxLayout()
        role_layout.addWidget(QLabel("Role:"))
        self.role_group = QButtonGroup()
        roles = self.config['entity']['roles']
        role_shortcuts = {'actor': 'Q', 'subject': 'W', 'related': 'E'}
        self.role_buttons = {}
        for i, role in enumerate(roles):
            shortcut_key = role_shortcuts.get(role, '')
            rb = QRadioButton(f"{role.capitalize()} [{shortcut_key}]")
            self.role_group.addButton(rb, i)
            role_layout.addWidget(rb)
            self.role_buttons[role] = rb
            if i == 0:
                rb.setChecked(True)
        self.role_group.buttonClicked.connect(self.on_entity_changed)
        entity_layout.addLayout(role_layout)

        # ID selection
        id_layout = QVBoxLayout()
        id_layout.addWidget(QLabel("ID (0-9):"))
        self.id_spin = QSpinBox()
        self.id_spin.setMinimum(0)
        self.id_spin.setMaximum(self.config['entity']['max_ids_per_role'] - 1)
        self.id_spin.setValue(0)
        self.id_spin.valueChanged.connect(self.on_entity_changed)
        id_layout.addWidget(self.id_spin)

        # ID shortcut hint
        id_hint = QLabel("Keys: 1→0, 2→1, ..., 0→9")
        id_hint.setStyleSheet("color: gray; font-size: 9px; font-style: italic;")
        id_layout.addWidget(id_hint)

        self.entity_label = QLabel("→ actor0")
        self.entity_label.setStyleSheet("font-weight: bold;")
        id_layout.addWidget(self.entity_label)
        entity_layout.addLayout(id_layout)

        # Tool selection
        tool_layout = QVBoxLayout()
        tool_layout.addWidget(QLabel("Tool:"))
        self.tool_group = QButtonGroup()
        tools = [('bbox', 'BBox', 'Z'), ('pos_point', 'Pos Point', 'X'), ('neg_point', 'Neg Point', 'C')]
        self.tool_buttons = {}
        for i, (tool_id, tool_label, shortcut_key) in enumerate(tools):
            rb = QRadioButton(f"{tool_label} [{shortcut_key}]")
            self.tool_group.addButton(rb, i)
            tool_layout.addWidget(rb)
            self.tool_buttons[tool_id] = rb
            if i == 0:
                rb.setChecked(True)
        self.tool_group.buttonClicked.connect(self.on_tool_changed)
        entity_layout.addLayout(tool_layout)

        layout.addWidget(entity_group)

        # Canvas viewer
        layout.addWidget(QLabel("Frame Viewer:"))
        self.canvas_viewer = CanvasViewer()
        self.canvas_viewer.drawing_completed.connect(self.on_auto_save)
        layout.addWidget(self.canvas_viewer)

        # Status label for save feedback
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)

        # Current annotations list
        layout.addWidget(QLabel("Current Annotations:"))
        self.annotations_list = AnnotationListWidget()
        self.annotations_list.setMaximumHeight(150)
        self.annotations_list.delete_requested.connect(self.on_delete_annotation)
        layout.addWidget(self.annotations_list)

        self.delete_ann_btn = QPushButton("🗑️ Delete Selected [Del]")
        self.delete_ann_btn.clicked.connect(self.on_delete_annotation)
        layout.addWidget(self.delete_ann_btn)

        return panel

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Store shortcuts to prevent garbage collection
        self.shortcuts = []

        shortcuts_map = [
            # Frame Navigation
            ('A', self.on_prev_anchor),
            ('D', self.on_next_anchor),
            ('F', self.on_carry_forward),
            # Video Navigation
            ('Ctrl+A', self.on_prev_video),
            ('Ctrl+D', self.on_next_video),
            # Export
            ('Ctrl+S', self.on_export),
            # Undo/Redo
            ('Ctrl+Z', self.on_undo),
            ('Ctrl+Shift+Z', self.on_redo),
            # Role selection
            ('Q', lambda: self.select_role('actor')),
            ('W', lambda: self.select_role('subject')),
            ('E', lambda: self.select_role('related')),
            # Tool selection
            ('Z', lambda: self.select_tool('bbox')),
            ('X', lambda: self.select_tool('pos_point')),
            ('C', lambda: self.select_tool('neg_point')),
            # ID selection (1-9 for ID 0-8, 0 for ID 9)
            ('1', lambda: self.select_id(0)),
            ('2', lambda: self.select_id(1)),
            ('3', lambda: self.select_id(2)),
            ('4', lambda: self.select_id(3)),
            ('5', lambda: self.select_id(4)),
            ('6', lambda: self.select_id(5)),
            ('7', lambda: self.select_id(6)),
            ('8', lambda: self.select_id(7)),
            ('9', lambda: self.select_id(8)),
            ('0', lambda: self.select_id(9)),
        ]

        for key, func in shortcuts_map:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(func)
            self.shortcuts.append(shortcut)

    def get_selected_role(self):
        """Get currently selected role"""
        for role, btn in self.role_buttons.items():
            if btn.isChecked():
                return role
        return 'actor'

    def get_selected_entity(self):
        """Get currently selected entity (role + ID)"""
        role = self.get_selected_role()
        entity_id = self.id_spin.value()
        return f"{role}{entity_id}"

    def get_selected_tool(self):
        """Get currently selected tool"""
        for tool, btn in self.tool_buttons.items():
            if btn.isChecked():
                return tool
        return 'bbox'

    def select_role(self, role):
        """Select role by shortcut"""
        if role in self.role_buttons:
            self.role_buttons[role].setChecked(True)
            self.on_entity_changed()

    def select_tool(self, tool):
        """Select tool by shortcut"""
        if tool in self.tool_buttons:
            self.tool_buttons[tool].setChecked(True)
            self.on_tool_changed()

    def select_id(self, id_num):
        """Select ID by shortcut"""
        max_id = self.config['entity']['max_ids_per_role']
        if 0 <= id_num < max_id:
            self.id_spin.setValue(id_num)
            self.on_entity_changed()

    def on_display_width_changed(self, value):
        """Display width slider changed"""
        self.display_width_label.setText(str(value))
        self.refresh_canvas()

    def on_dataset_changed(self, dataset):
        """Dataset selection changed"""
        # Clear video combo when dataset changes
        self.video_combo.clear()

        # Skip if placeholder is selected
        if not dataset or dataset.startswith("--"):
            self.video_combo.addItem("-- Select Video --")
            return

        if dataset == "ucf-crime":
            self.current_adapter = UCFCrimeAdapter(
                self.config['dataset']['ucf_crime']['annotation_file'],
                original_fps=self.config['dataset']['ucf_crime']['original_fps']
            )
        elif dataset == "xd-violence":
            self.current_adapter = XDViolenceAdapter(
                self.config['dataset']['xd_violence']['annotation_file'],
                original_fps=self.config['dataset']['xd_violence']['original_fps'],
                gap_threshold=self.config['dataset']['xd_violence']['gap_threshold']
            )
        else:
            return

        videos = self.current_adapter.get_videos()
        self.video_combo.addItem("-- Select Video --")
        for v in videos:
            # Use display_name if available, otherwise use name
            display = v.get('display_name', v['name'])
            self.video_combo.addItem(display)

    def on_video_changed(self, video_display_name):
        """Video selection changed"""
        if not video_display_name or video_display_name.startswith("--"):
            return

        if not self.current_adapter:
            return

        videos = self.current_adapter.get_videos()
        # Find video by display_name
        self.current_video = next((v for v in videos if v.get('display_name', v['name']) == video_display_name), None)

        if not self.current_video:
            return

        # Create unique video identifier including interval
        video_id = f"{self.current_video['name']}_interval{self.current_video.get('interval_idx', 0)}"

        # Update annotation state
        if self.ann_state.current_video != video_id:
            self.ann_state.annotations.clear()
            self.ann_state.entity_notes.clear()
            self.ann_state.history.clear()
            self.ann_state.history_idx = -1

        self.load_video_and_anchors()

    def on_dt_changed(self, dt_mode):
        """Dt mode changed"""
        if self.current_video:
            self.load_video_and_anchors()

    def load_video_and_anchors(self):
        """Load video and generate anchors"""
        if not self.current_video:
            return

        dataset = self.dataset_combo.currentText()
        video_path = get_video_path(
            self.config['dataset'][dataset.replace('-', '_')]['videos_dir'],
            self.current_video['name']
        )

        if not os.path.exists(video_path):
            QMessageBox.warning(self, "Error", f"Video file not found: {video_path}")
            return

        # Load video
        if self.video_loader:
            self.video_loader.release()
        self.video_loader = VideoLoader(video_path)
        info = self.video_loader.get_info()

        # Generate anchors
        intervals = self.current_video['intervals']
        if not intervals:
            QMessageBox.warning(self, "Warning", "No anomaly intervals found for this video")
            return

        t0, t1 = intervals[0]

        # Determine dt
        dt_mode = self.dt_combo.currentText()
        if dt_mode == "AUTO":
            dt = select_dt_auto(
                t1 - t0,
                self.config['eis']['dt_candidates'],
                self.config['eis']['min_K'],
                self.config['eis']['max_K']
            )
        else:
            dt = int(dt_mode[:-1])

        # Expand interval
        t0_prime, t1_prime = self.current_adapter.expand_interval(t0, t1, dt)

        # Generate anchors
        anchors = generate_anchors(t0_prime, t1_prime, dt)
        K = len(anchors)

        # Handle edge cases
        if K > self.config['eis']['max_K']:
            anchors = subsample_anchors(anchors, self.config['eis']['max_K'])
            K = len(anchors)
        elif K < self.config['eis']['min_K']:
            anchors = pad_anchors(anchors, self.config['eis']['min_K'])
            K = len(anchors)

        self.anchors = anchors

        # Create unique video identifier including interval
        video_id = f"{self.current_video['name']}_interval{self.current_video.get('interval_idx', 0)}"

        # Update annotation state
        self.ann_state.set_video(
            video_id,
            anchors,
            dt,
            info['width'],
            info['height']
        )

        # Update timeline info
        self.timeline_info_label.setText(
            f"Interval: [{t0}, {t1}] → [{t0_prime}, {t1_prime}] (expanded by Δt={dt}) | K = {K}"
        )

        # Create timeline buttons
        for i in reversed(range(self.timeline_layout.count())):
            self.timeline_layout.itemAt(i).widget().setParent(None)

        self.timeline_buttons = []
        for i, anchor in enumerate(anchors):
            btn = QPushButton(f"{anchor}s")
            btn.clicked.connect(lambda checked, idx=i: self.jump_to_anchor(idx))
            self.timeline_layout.addWidget(btn)
            self.timeline_buttons.append(btn)

        # Update timeline colors
        self.update_timeline_colors()

        # Load first frame
        self.jump_to_anchor(0)

    def update_timeline_colors(self):
        """Update timeline button colors based on annotation status"""
        if not self.timeline_buttons or not self.anchors:
            return

        current_idx = self.ann_state.current_anchor_idx

        for i, (btn, anchor_sec) in enumerate(zip(self.timeline_buttons, self.anchors)):
            annotations = self.ann_state.get_annotations_for_frame(anchor_sec)
            has_annotations = bool(annotations)
            is_current = (i == current_idx)

            # Set style based on status
            if is_current and has_annotations:
                # Current frame with annotations: green background + blue border
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #90EE90;
                        border: 3px solid #4169E1;
                        font-weight: bold;
                    }
                """)
            elif is_current:
                # Current frame without annotations: blue border only
                btn.setStyleSheet("""
                    QPushButton {
                        border: 3px solid #4169E1;
                        font-weight: bold;
                    }
                """)
            elif has_annotations:
                # Has annotations: green background
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #90EE90;
                    }
                """)
            else:
                # Empty frame: default style
                btn.setStyleSheet("")

    def jump_to_anchor(self, idx):
        """Jump to specific anchor"""
        if 0 <= idx < len(self.anchors):
            self.ann_state.current_anchor_idx = idx
            self.update_timeline_colors()
            self.load_current_frame()

    def load_current_frame(self):
        """Load and display current frame"""
        if not self.anchors or not self.video_loader:
            return

        idx = self.ann_state.current_anchor_idx
        anchor_sec = self.anchors[idx]

        # Calculate progress statistics
        total_frames = len(self.anchors)
        annotated_count = sum(1 for a in self.anchors if self.ann_state.get_annotations_for_frame(a))
        progress_percent = int(annotated_count / total_frames * 100) if total_frames > 0 else 0
        current_annotations = self.ann_state.get_annotations_for_frame(anchor_sec)
        current_ann_count = len(current_annotations)

        # Update label with progress stats
        self.current_frame_label.setText(
            f"Frame: {anchor_sec}s ({idx + 1}/{total_frames}) | "
            f"📊 {annotated_count}/{total_frames} ({progress_percent}%) | "
            f"📝 {current_ann_count}"
        )

        # Load frame
        frame_rgb = self.video_loader.seek_to_second(anchor_sec)

        if frame_rgb is None:
            QMessageBox.warning(self, "Error", "Failed to load frame")
            return

        self.current_frame = frame_rgb
        self.refresh_canvas()
        self.update_annotations_list()

    def refresh_canvas(self):
        """Refresh canvas with current frame and annotations"""
        if self.current_frame is None:
            return

        display_width = self.display_width_slider.value()
        self.canvas_viewer.set_image(self.current_frame, display_width)

        # Draw existing annotations
        anchor_sec = self.anchors[self.ann_state.current_anchor_idx]
        annotations = self.ann_state.get_annotations_for_frame(anchor_sec)
        self.canvas_viewer.draw_annotations(annotations, self.config)

        # Update canvas drawing mode
        tool = self.get_selected_tool()
        role = self.get_selected_role()
        color = self.config['ui']['colors'].get(role, '#FF0000')
        self.canvas_viewer.set_drawing_mode(tool, color)

    def update_annotations_list(self):
        """Update current annotations list"""
        self.annotations_list.clear()

        anchor_sec = self.anchors[self.ann_state.current_anchor_idx]
        annotations = self.ann_state.get_annotations_for_frame(anchor_sec)

        if not annotations:
            item = QListWidgetItem("No annotations for this frame yet")
            self.annotations_list.addItem(item)
            return

        for entity_id, data in annotations.items():
            parts = []
            if data['bbox']:
                parts.append("bbox ✓")
            if data['pos_points']:
                parts.append(f"pos_points ({len(data['pos_points'])})")
            if data['neg_points']:
                parts.append(f"neg_points ({len(data['neg_points'])})")

            text = f"{entity_id}: {', '.join(parts)}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entity_id)
            self.annotations_list.addItem(item)

    def on_entity_changed(self):
        """Entity selection changed"""
        entity = self.get_selected_entity()
        self.entity_label.setText(f"→ {entity}")

        # Update canvas color
        role = self.get_selected_role()
        tool = self.get_selected_tool()
        color = self.config['ui']['colors'].get(role, '#FF0000')
        self.canvas_viewer.set_drawing_mode(tool, color)

        # Load entity note
        self.load_entity_note()

    def load_entity_note(self):
        """Load note for current entity"""
        entity = self.get_selected_entity()
        note = self.ann_state.get_entity_note(entity)

        # Block signals while updating to avoid triggering on_entity_note_changed
        self.entity_notes_input.blockSignals(True)
        self.entity_notes_input.setPlainText(note)
        self.entity_notes_input.blockSignals(False)

    def on_entity_note_changed(self):
        """Entity note text changed"""
        entity = self.get_selected_entity()
        note = self.entity_notes_input.toPlainText()
        self.ann_state.set_entity_note(entity, note)

    def on_tool_changed(self):
        """Tool selection changed"""
        tool = self.get_selected_tool()
        role = self.get_selected_role()
        color = self.config['ui']['colors'].get(role, '#FF0000')
        self.canvas_viewer.set_drawing_mode(tool, color)

    def on_prev_anchor(self):
        """Go to previous anchor"""
        idx = self.ann_state.current_anchor_idx
        if idx > 0:
            self.jump_to_anchor(idx - 1)

    def on_next_anchor(self):
        """Go to next anchor"""
        idx = self.ann_state.current_anchor_idx
        if idx < len(self.anchors) - 1:
            self.jump_to_anchor(idx + 1)

    def on_prev_video(self):
        """Go to previous video"""
        current_idx = self.video_combo.currentIndex()
        if current_idx > 0:
            self.video_combo.setCurrentIndex(current_idx - 1)
            self.show_status("Previous video", 1500)

    def on_next_video(self):
        """Go to next video"""
        current_idx = self.video_combo.currentIndex()
        if current_idx < self.video_combo.count() - 1:
            self.video_combo.setCurrentIndex(current_idx + 1)
            self.show_status("Next video", 1500)

    def on_undo(self):
        """Undo last action"""
        if self.ann_state.undo():
            self.refresh_canvas()
            self.update_annotations_list()
            self.update_timeline_colors()

    def on_redo(self):
        """Redo last undone action"""
        if self.ann_state.redo():
            self.refresh_canvas()
            self.update_annotations_list()
            self.update_timeline_colors()

    def on_carry_forward(self):
        """Carry forward bbox from previous frame"""
        idx = self.ann_state.current_anchor_idx
        if idx <= 0:
            return

        prev_anchor = self.anchors[idx - 1]
        current_anchor = self.anchors[idx]
        entity = self.get_selected_entity()

        success = self.ann_state.carry_forward_bbox(prev_anchor, current_anchor, entity)

        if success:
            self.show_status(f"Copied bbox from frame {prev_anchor} ✓", 2000)
            self.refresh_canvas()
            self.update_annotations_list()
            self.update_timeline_colors()
        else:
            self.show_status(f"No bbox found at frame {prev_anchor}", 2000)

    def on_auto_save(self):
        """Auto-save annotation after drawing"""
        obj_data = self.canvas_viewer.get_last_drawn_object()

        if not obj_data:
            # Clear drawing state even if nothing to save
            self.canvas_viewer.clear_drawing_state()
            return

        obj_type, coords = obj_data
        anchor_sec = self.anchors[self.ann_state.current_anchor_idx]
        entity = self.get_selected_entity()
        tool = self.get_selected_tool()

        if obj_type == 'bbox':
            self.ann_state.add_bbox(anchor_sec, entity, coords)
            self.show_status("BBox saved ✓", 2000)
        elif obj_type == 'point':
            self.ann_state.add_point(anchor_sec, entity, coords, tool)
            self.show_status(f"{tool} saved ✓", 2000)

        # Clear drawing state after saving
        self.canvas_viewer.clear_drawing_state()

        self.refresh_canvas()
        self.update_annotations_list()
        self.update_timeline_colors()


    def show_status(self, message, duration=2000):
        """Show status message temporarily"""
        self.status_label.setText(message)
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    def on_delete_annotation(self):
        """Delete selected annotation"""
        item = self.annotations_list.currentItem()
        if not item:
            return

        entity_id = item.data(Qt.UserRole)
        if not entity_id:
            return

        anchor_sec = self.anchors[self.ann_state.current_anchor_idx]
        self.ann_state.delete_annotation(anchor_sec, entity_id)

        self.refresh_canvas()
        self.update_annotations_list()
        self.update_timeline_colors()

    def on_import(self):
        """Import existing annotations"""
        run_name = self.run_name_input.text()

        if not self.current_video:
            QMessageBox.warning(self, "Warning", "Please select a video first")
            return

        video_name = self.current_video['name']
        interval_idx = self.current_video.get('interval_idx')

        import_path = get_annotation_path(
            self.config['export']['output_dir'],
            run_name,
            video_name,
            interval_idx
        )

        if not os.path.exists(import_path):
            QMessageBox.warning(self, "Warning", "No existing annotation found")
            return

        try:
            imported = import_annotations(
                import_path,
                self.ann_state.video_width,
                self.ann_state.video_height
            )
            self.ann_state.import_from_list(imported)
            self.show_status(f"Imported {len(imported)} annotations ✓", 3000)
            self.refresh_canvas()
            self.update_annotations_list()
            self.update_timeline_colors()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed: {e}")

    def on_export(self):
        """Export current video annotations"""
        annotations = self.ann_state.export_to_list()

        if not annotations:
            QMessageBox.warning(self, "Warning", "No annotations to export for this video")
            return

        # Validate
        is_valid, errors = validate_annotations(annotations)

        if not is_valid:
            error_msg = "Validation failed:\n" + "\n".join([f"  - {err}" for err in errors])
            QMessageBox.critical(self, "Validation Error", error_msg)
            return

        # Export
        run_name = self.run_name_input.text()
        video_name = self.current_video['name']
        interval_idx = self.current_video.get('interval_idx')

        output_path = get_annotation_path(
            self.config['export']['output_dir'],
            run_name,
            video_name,
            interval_idx
        )

        try:
            export_annotations(
                annotations,
                self.ann_state.video_width,
                self.ann_state.video_height,
                output_path
            )

            # Generate stats
            stats = generate_statistics(annotations)

            # Get filename for display
            filename = os.path.basename(output_path)

            # Show brief status message
            self.show_status(f"Exported {stats['total_annotations']} annotations to {filename} ✓", 3000)

            # Print stats to console for reference
            print(f"\n=== Export Success ===")
            print(f"File: {output_path}")
            print(f"Total frames: {stats['total_frames']}")
            print(f"Total annotations: {stats['total_annotations']}")
            print(f"Entities: {', '.join(stats['entities'])}")
            for entity_id, counts in stats['per_entity'].items():
                print(f"  {entity_id}: bbox={counts['bbox']}, pos={counts['pos_point']}, neg={counts['neg_point']}")
            print("=====================\n")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        # Ignore shortcuts when typing in input fields
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, (QLineEdit, QSpinBox)):
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Frame Navigation
        if key == Qt.Key_A and modifiers == Qt.NoModifier:
            self.on_prev_anchor()
            event.accept()
        elif key == Qt.Key_D and modifiers == Qt.NoModifier:
            self.on_next_anchor()
            event.accept()
        elif key == Qt.Key_F and modifiers == Qt.NoModifier:
            self.on_carry_forward()
            event.accept()
        # Video Navigation
        elif key == Qt.Key_A and modifiers == Qt.ControlModifier:
            self.on_prev_video()
            event.accept()
        elif key == Qt.Key_D and modifiers == Qt.ControlModifier:
            self.on_next_video()
            event.accept()
        # Export
        elif key == Qt.Key_S and modifiers == Qt.ControlModifier:
            self.on_export()
            event.accept()
        # Undo/Redo
        elif key == Qt.Key_Z and modifiers == Qt.ControlModifier:
            self.on_undo()
            event.accept()
        elif key == Qt.Key_Z and modifiers == (Qt.ControlModifier | Qt.ShiftModifier):
            self.on_redo()
            event.accept()
        # Role selection
        elif key == Qt.Key_Q and modifiers == Qt.NoModifier:
            self.select_role('actor')
            event.accept()
        elif key == Qt.Key_W and modifiers == Qt.NoModifier:
            self.select_role('subject')
            event.accept()
        elif key == Qt.Key_E and modifiers == Qt.NoModifier:
            self.select_role('related')
            event.accept()
        # Tool selection
        elif key == Qt.Key_Z and modifiers == Qt.NoModifier:
            self.select_tool('bbox')
            event.accept()
        elif key == Qt.Key_X and modifiers == Qt.NoModifier:
            self.select_tool('pos_point')
            event.accept()
        elif key == Qt.Key_C and modifiers == Qt.NoModifier:
            self.select_tool('neg_point')
            event.accept()
        # ID selection
        elif key == Qt.Key_1 and modifiers == Qt.NoModifier:
            self.select_id(0)
            event.accept()
        elif key == Qt.Key_2 and modifiers == Qt.NoModifier:
            self.select_id(1)
            event.accept()
        elif key == Qt.Key_3 and modifiers == Qt.NoModifier:
            self.select_id(2)
            event.accept()
        elif key == Qt.Key_4 and modifiers == Qt.NoModifier:
            self.select_id(3)
            event.accept()
        elif key == Qt.Key_5 and modifiers == Qt.NoModifier:
            self.select_id(4)
            event.accept()
        elif key == Qt.Key_6 and modifiers == Qt.NoModifier:
            self.select_id(5)
            event.accept()
        elif key == Qt.Key_7 and modifiers == Qt.NoModifier:
            self.select_id(6)
            event.accept()
        elif key == Qt.Key_8 and modifiers == Qt.NoModifier:
            self.select_id(7)
            event.accept()
        elif key == Qt.Key_9 and modifiers == Qt.NoModifier:
            self.select_id(8)
            event.accept()
        elif key == Qt.Key_0 and modifiers == Qt.NoModifier:
            self.select_id(9)
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Clean up on close"""
        if self.video_loader:
            self.video_loader.release()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
