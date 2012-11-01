from random import randint
from math import ceil, hypot
from time import time
from os import path
from PyQt4.QtGui import *
from PyQt4.QtCore import QRectF
from PyQt4.Qt import Qt
from . import settings


class Effect(object):
    finished = False
    upd_time = settings.effects_update_time

    def __init__(self, callback=None):
        self.callback = callback if callback else lambda: None

    def run(self, time_delta):
        pass


class ChangeRadius(Effect):

    def __init__(self, scene, pixmap, pos, callback=None):
        super(ChangeRadius, self).__init__(callback)
        self.scene = scene
        self.obj = obj = scene.addPixmap(pixmap)
        obj.setZValue(2)
        obj.setTransformOriginPoint(
            obj.boundingRect().width() / 2,
            obj.boundingRect().height() / 2
        )
        pos = list(pos)
        pos[0] -= pixmap.width() / 2
        pos[1] -= pixmap.height() / 2
        obj.setPos(*pos)


class Collapsing(ChangeRadius):

    def run(self, time_delta):
        factor = time_delta / self.upd_time
        self.obj.setScale(self.obj.scale() - 0.1 * factor)
        if self.obj.scale() < 0.1:
            self.scene.removeItem(self.obj)
            self.finished = True


class Inflation(ChangeRadius):

    def __init__(self, scene, pixmap, pos, callback=None):
        super(Inflation, self).__init__(scene, pixmap, pos, callback)
        self.obj.setScale(0.1)
        self.callback = callback

    def run(self, time_delta):
        factor = time_delta / self.upd_time
        self.obj.setScale(self.obj.scale() + 0.1 * factor)
        if self.obj.scale() >= 1.0:
            self.scene.removeItem(self.obj)
            self.finished = True


class Explosion(Effect):

    def __init__(self, scene, pos, radius, callback=None, count=1):
        from .space import Pixmap

        self.scene = scene
        super(Explosion, self).__init__(callback)
        pos = list(pos)
        parts = self.parts = []
        pixmap = Pixmap(path.join(settings.effects_path, settings.bang_image))
        pixmap = pixmap.scaledToHeight(radius * 2)
        pos[0] -= pixmap.width() / 2
        pos[1] -= pixmap.height() / 2
        for i in range(count):
            parts.append(scene.addPixmap(pixmap))
        for part in parts:
            part.setTransformOriginPoint(
                part.boundingRect().width() / 2,
                part.boundingRect().height() / 2
            )
            part.setPos(*pos)
            part.setScale(0.1)
            part.setZValue(3)
            part.setRotation(randint(0, 360))

    def run(self, time_delta):
        factor = time_delta / self.upd_time
        for part in self.parts:
            scale = part.scale() + (1 - part.scale()) / 5 * factor
            part.setScale(scale)

            if part.scale() > 0.8:
                opacity = 0.98 - (part.scale() - 0.8) / 0.18
                part.setOpacity(opacity)
            if part.scale() > 0.98:
                self.scene.removeItem(part)
                self.finished = True


class PlanetMerging(Effect):
    time = 80 * Effect.upd_time
    growing_part = 0.25

    def __init__(self, pl, start_px, end_px, start_r, end_r):
        super(PlanetMerging, self).__init__()
        self.start_time = time()
        self.pl = pl
        self.start_px = start_px.scaledToHeight(end_r * 2)
        self.end_px = end_px.scaledToHeight(end_r * 2)
        self.radius = start_r
        self.start_r = start_r
        self.end_r = end_r

    def run(self, time_delta):
        r_diff = float(self.end_r - self.start_r)
        r_step = r_diff / (self.time * self.growing_part) * time_delta
        if self.radius < self.end_r:
            self.radius += r_step
        r = int(ceil(min(self.radius, self.end_r)))
        pl = self.pl
        imp = pl.speed * pl.mass
        pl.radius = r
        pl.speed = imp / pl.mass
        new_px = self.end_px.scaledToHeight(r * 2)
        painter = QPainter(new_px)
        painter.setOpacity(1.0 - 1.0 / self.time * (time() - self.start_time))
        painter.drawPixmap(0, 0, self.start_px.scaledToHeight(r * 2))
        painter.end()
        pl.setPixmap(new_px)
        pl.update_total_mass()
        if time() > time() + self.time:
            self.finished = True


class WormHole(QGraphicsItem):
    rim_color = '#000'
    rotation_angle = 0.5
    current_angle = 0
    captured = False
    outgoing = None
    bckg_square = None

    def __init__(self, radius, pos):
        super(WormHole, self).__init__()
        self.radius = radius
        self.setPos(*pos)
        self.setZValue(0)
        self.setTransformOriginPoint(radius, radius)
        self.show_pl = []

    def delete(self):
        scene = self.scene()
        scene.hot_keys_enabled = True
        scene.wh_pair.remove(self)
        scene.removeItem(self)


    def other(self, pair):
        assert len(pair) <= 2
        if len(pair) == 1:
            return None
        wh1, wh2 = pair
        return wh1 if not wh1 is self else wh2

    def boundingRect(self):
        r = self.radius
        return QRectF(0, 0, r * 2, r * 2)

    def paint(self, painter, option, widget):
        r = self.radius
        img_r = r * 0.9

        painter.setClipping(True)
        _path = QPainterPath()
        _path.addEllipse(
            int(r - img_r), int(r - img_r),
            img_r * 2, img_r * 2,
        )
        painter.setClipPath(_path)
        pxmp = self.bckg_square
        if pxmp:
            pxmp = pxmp.scaledToHeight(r * 2)
            painter.drawPixmap(0, 0, pxmp)
        else:
            painter.fillRect(0, 0, r * 2, r * 2, QColor(self.rim_color))
        painter.setClipping(False)

        grad = QRadialGradient(r, r, r)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.8, QColor(0, 0, 0, 0))
        grad.setColorAt(0.9, QColor(self.rim_color))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        brush = QBrush(grad)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, r * 2, r * 2)

    def update_bckg_square(self, bckg_item):
        bckg_pxmp = bckg_item.pixmap()
        r = settings.maximum_wormhole_radius
        d = r * 2
        x, y = self.position[0] - r, self.position[1] - r
        x = max(min(x, bckg_pxmp.width() - d), 0)
        y = max(min(y, bckg_pxmp.height() - d), 0)
        pixmap = bckg_pxmp.copy(x, y, d, d)
        painter = QPainter(pixmap)
        for pl in self.show_pl:
            pl_r = pl.radius
            r_atm = pl_r * 1.1
            img = QImage(r_atm * 2, r_atm * 2, 6)
            img.fill(0)
            img_p = QPainter(img)
            img_p.drawPixmap(r_atm - pl_r, r_atm - pl_r, pl.pixmap())
            pl.draw_atmosphere(img_p, 0)
            img_p.end()

            px, py = pl.pos().x(), pl.pos().y()
            p1, p2 = px - x, py - y
            painter.drawImage(p1, p2, img)
        painter.end()
        self.show_pl = []
        return pixmap

    def _update(self, pair, planets, bckg_item, time_delta):
        other = self.other(pair)
        pos = self.position
        if other:
            self.rotation_angle = -other.rotation_angle
            self.bckg_square = other.update_bckg_square(bckg_item)
            for pl in planets:
                pl_pos = pl.position
                x, y = pl_pos[0] - pos[0], pl_pos[1] - pos[1]
                dist = hypot(x, y)
                if dist < self.radius:
                    self.process(other, pl)
                elif self.outgoing is pl:
                    self.outgoing = None

                if dist < pl.radius + settings.maximum_wormhole_radius:
                    self.show_pl.append(pl)
        else:
            self.bckg_square = None
        self.update()

        factor = time_delta / Effect.upd_time
        self.current_angle += self.rotation_angle * factor
        self.setRotation(self.current_angle)

    def process(self, other, pl):
        if self.outgoing is pl: return
        if self.radius < pl.radius: return
        if other.radius < pl.radius: return
        if pl.captured: return
        pl.position = list(other.position)
        other.outgoing = pl

    def setPos(self, x, y):
        self.position = (x, y,)
        x -= self.radius
        y -= self.radius
        super(WormHole, self).setPos(x, y)

    def mousePressEvent(self, event):
        a = self.scene().window.action
        if a is None:
            self.scene().hot_keys_enabled = False
            self.captured = True
            point = event.scenePos()
            self.setPos(point.x(), point.y())
        elif a == 'del':
            self.delete()

    def mouseReleaseEvent(self, event):
        if self.scene().window.action is None:
            self.scene().hot_keys_enabled = True
            self.captured = False

    def mouseMoveEvent(self, event):
        if self.captured:
            point = event.scenePos()
            self.setPos(point.x(), point.y())

    def to_dict(self):
        return {
            'radius': self.radius,
            'pos': self.position,
        }
