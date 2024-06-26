import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QSizePolicy, QWidget

from .viewer import ImageViewer


class TimePlot(pg.PlotWidget):

    def __init__(
        self,
        parent: QWidget,
        image_viewer: pg.ImageView,
        norm_range: pg.LinearRegionItem,
        **kargs,
    ) -> None:
        super().__init__(parent, **kargs)
        self.hideAxis('left')
        self.addItem(image_viewer.timeLine)
        self.timeline = image_viewer.timeLine
        self.timeline.setMovable(False)
        self.addItem(image_viewer.frameTicks)
        self.addItem(image_viewer.normRgn)
        self.old_roi_plot = image_viewer.ui.roiPlot
        self.old_roi_plot.setParent(None)
        self.image_viewer = image_viewer
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(0, 40))
        self.norm_range = norm_range
        self.addItem(self.norm_range)
        self.norm_range.hide()
        self._accept_all_events = False

    def toggle_norm_range(self) -> None:
        if self.norm_range.isVisible():
            self.norm_range.hide()
        else:
            self.norm_range.show()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
        else:
            rotation = event.angleDelta().y()
            if rotation < 0:
                pos = self.timeline.getPos()
                self.timeline.setPos((pos[0]+1, pos[1]))
            if rotation > 0:
                pos = self.timeline.getPos()
                self.timeline.setPos((pos[0]-1, pos[1]))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (event.modifiers() == Qt.KeyboardModifier.NoModifier
                and event.button() == Qt.MouseButton.LeftButton
                and not self.norm_range.isVisible()):
            x = self.plotItem.vb.mapSceneToView(  # type: ignore
                event.pos()
            ).x()
            self.image_viewer.setCurrentIndex(round(x))
            event.accept()
        elif ((self.norm_range.isVisible()
                    and (self.norm_range.mouseHovering
                        or self.norm_range.childItems()[0].mouseHovering
                        or self.norm_range.childItems()[1].mouseHovering))
                or not self.norm_range.isVisible()):
            super().mousePressEvent(event)
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        self.image_viewer.keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        super().keyReleaseEvent(event)
        self.image_viewer.keyReleaseEvent(event)


class MeasureROI(pg.PolyLineROI):

    def __init__(self, viewer: ImageViewer) -> None:
        self._viewer = viewer
        super().__init__([[0, 0], [0, 20], [10, 10]], closed=True)
        self.handleSize = 10
        self.sigRegionChanged.connect(self.update_labels)

        self.n_px: int = 1
        self.px_in_mm: float = 1
        self.show_in_mm = False

        self.line_labels = []
        self.angle_labels = []

        self._viewer.view.addItem(self)
        self.setPen(color=(128, 128, 0, 100), width=3)
        self._visible = True
        self.toggle()
        self._viewer.image_changed.connect(self.reshape)

    def reshape(self) -> None:
        height = self._viewer.image.shape[2]
        width = self._viewer.image.shape[1]
        self.toggle()
        self.setPoints([[0, 0], [0, 0.5*height], [0.5*width, 0.25*height]])
        self.toggle()

    def toggle(self) -> None:
        self._visible = not self._visible
        self.setVisible(self._visible)
        for label in self.line_labels:
            label.setVisible(self._visible)
        for label in self.angle_labels:
            label.setVisible(self._visible)
        if self._visible:
            self.update_labels()

    def update_labels(self) -> None:
        self.update_angles()
        self.update_lines()

    def update_angles(self) -> None:
        positions = self.getSceneHandlePositions()

        while len(self.angle_labels) > len(positions):
            label = self.angle_labels.pop()
            self._viewer.view.removeItem(label)

        for i, (_, pos) in enumerate(positions):
            _, prev_pos = positions[(i - 1) % len(positions)]
            _, next_pos = positions[(i + 1) % len(positions)]
            angle = pg.Point(pos - next_pos).angle(
                pg.Point(pos - prev_pos)
            )
            pos = self._viewer.view.mapToView(pos)
            if i < len(self.angle_labels):
                self.angle_labels[i].setPos(pos.x(), pos.y())
                self.angle_labels[i].setText(f"{angle:.2f}°")
            else:
                angle_label = pg.TextItem(f"{angle:.2f}°")
                angle_label.setPos(pos.x(), pos.y())
                self._viewer.view.addItem(angle_label)
                self.angle_labels.append(angle_label)

    def update_lines(self) -> None:
        positions = self.getSceneHandlePositions()

        while len(self.line_labels) > len(positions):
            label = self.line_labels.pop()
            self._viewer.view.removeItem(label)

        for i, (_, pos) in enumerate(positions):
            _, next_pos = positions[(i + 1) % len(positions)]
            pos = self._viewer.view.mapToView(pos)
            next_pos = self._viewer.view.mapToView(next_pos)
            length = pg.Point(pos - next_pos).length()
            mid = (pos + next_pos) / 2
            if self.show_in_mm:
                length = length * self.px_in_mm / self.n_px
            pos = self._viewer.view.mapToView(pos)
            if i < len(self.line_labels):
                self.line_labels[i].setPos(mid.x(), mid.y())
                self.line_labels[i].setText(f"{length:.2f}")
            else:
                angle_label = pg.TextItem(f"{length:.2f}")
                angle_label.setPos(mid.x(), mid.y())
                self._viewer.view.addItem(angle_label)
                self.line_labels.append(angle_label)


class ExtractionLine(pg.InfiniteLine):

    def __init__(
        self,
        viewer: ImageViewer,
        vertical: bool = False,
    ) -> None:
        self._vertical = vertical
        super().__init__(
            angle=90 if vertical else 0,
            pen=pg.mkPen(
                color=(120, 120, 120, 200),
                style=Qt.PenStyle.DashLine,
                width=3,
            ),
            movable=True,
        )
        self._viewer = viewer
        self._viewer.view.addItem(self)
        self._upper = pg.InfiniteLine(
            angle=90 if self._vertical else 0,
            pen=pg.mkPen(
                color=(75, 75, 75, 200),
                style=Qt.PenStyle.DotLine,
                width=3,
            ),
            movable=False,
            hoverPen=pg.mkPen(
                color=(255, 0, 0, 200),
                style=Qt.PenStyle.DotLine,
                width=3,
            ),
        )
        self._lower = pg.InfiniteLine(
            angle=90 if self._vertical else 0,
            pen=pg.mkPen(
                color=(75, 75, 75, 200),
                style=Qt.PenStyle.DotLine,
                width=3,
            ),
            movable=False,
            hoverPen=pg.mkPen(
                color=(255, 0, 0, 200),
                style=Qt.PenStyle.DotLine,
                width=3,
            ),
        )
        self._width: int = 0
        self.sigPositionChanged.connect(self._move_bounds)

    def value(self) -> int:
        return super().value()  # type: ignore

    @property
    def width(self) -> int:
        return self._width

    def setMouseHover(self, hover) -> None:
        self._lower.setMouseHover(hover)
        self._upper.setMouseHover(hover)
        super().setMouseHover(hover)

    def setPos(self, p) -> None:
        if isinstance(p, (list, tuple, np.ndarray)) and not np.ndim(p) == 0:
            p = p[0] if self._vertical else p[1]
        elif isinstance(p, QPointF):
            p = p.x() if self._vertical else p.y()
        p = int(p) + 0.5  # type: ignore
        super().setPos(p)

    def _move_bounds(self) -> None:
        if self._bounds is not None:
            self._upper.setPos(self.value() - self._width - 0.5)
            self._lower.setPos(self.value() + self._width + 0.5)

    def change_width(self, width: int) -> None:
        if width == self._width or width < 0:
            return
        elif width == 0:
            self._viewer.view.removeItem(self._upper)
            self._viewer.view.removeItem(self._lower)
            self._width = 0
            return

        if self._width == 0:
            self._viewer.view.addItem(self._upper)
            self._viewer.view.addItem(self._lower)
        self._width = width
        self._move_bounds()

    def toggle(self) -> None:
        if self.movable:
            self.setMovable(False)
            self._viewer.view.removeItem(self)
            if self._width > 0:
                self._viewer.view.removeItem(self._upper)
                self._viewer.view.removeItem(self._lower)
        else:
            self.setMovable(True)
            self._viewer.view.addItem(self)
            if self._width > 0:
                self._viewer.view.addItem(self._upper)
                self._viewer.view.addItem(self._lower)


class ExtractionPlot(pg.PlotWidget):

    plotItem: pg.PlotItem

    def __init__(
        self,
        viewer: ImageViewer,
        vertical: bool = False,
        **kwargs,
    ) -> None:
        self._viewer = viewer
        self._vert = vertical
        self._width = 0  # n pixels above and below line to mean
        v_plot_viewbox = pg.ViewBox()
        if vertical:
            v_plot_viewbox.invertX()
            v_plot_viewbox.invertY()
        v_plot_item = pg.PlotItem(viewBox=v_plot_viewbox)
        v_plot_item.showGrid(x=True, y=True, alpha=0.4)
        super().__init__(plotItem=v_plot_item, **kwargs)

        self._extractionline = ExtractionLine(viewer=viewer, vertical=vertical)
        self._extractionline.sigPositionChanged.connect(self.draw_line)
        self._viewer.timeLine.sigPositionChanged.connect(self.draw_line)
        self._viewer.image_changed.connect(self.draw_line)
        self._viewer.image_size_changed.connect(self.center_line)
        self.center_line()

    def center_line(self) -> None:
        self._extractionline.setPos(
            self._viewer.image.shape[1 if self._vert else 2] / 2
        )

    def change_width(self, width: int) -> None:
        self._extractionline.change_width(width)
        self.draw_line()

    def draw_line(self) -> None:
        p = int(self._extractionline.value())  # type: ignore
        if not (0 <= p < self._viewer.image.shape[1 if self._vert else 2]):
            return
        self.clear()
        sp = slice(
            max(p - self._extractionline.width, 0),
            min(p + self._extractionline.width + 1,
                self._viewer.image.shape[1 if self._vert else 2])
        )
        if self._vert:
            image = self._viewer.now[sp, :].mean(axis=0)
        else:
            image = self._viewer.now[:, sp].mean(axis=1)
        self.plot(image)

    def plot(self, image: np.ndarray) -> None:
        if image.ndim == 2:
            if self._vert:
                x_values = np.arange(image.shape[0])
                self.plotItem.plot(image[:, 0], x_values, pen='r')
                self.plotItem.plot(image[:, 1], x_values, pen='g')
                self.plotItem.plot(image[:, 2], x_values, pen='b')
            else:
                self.plotItem.plot(image[:, 0], pen='r')
                self.plotItem.plot(image[:, 1], pen='g')
                self.plotItem.plot(image[:, 2], pen='b')
        else:
            if self._vert:
                x_values = np.arange(image.shape[0])
                self.plotItem.plot(image, x_values, pen='gray')
            else:
                self.plotItem.plot(image, pen='gray')

    def toggle_line(self) -> None:
        self._extractionline.toggle()
